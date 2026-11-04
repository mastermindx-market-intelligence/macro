"""Fixed upload boundaries of the incumbent merge-on-green job.

This is its protected-process adapter, not a second scheduler. All source and
credentials remain on the default-branch controller. GitHub artifacts are the
immutable receipts; local files are only same-job handoff between upload steps.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import io
import time
import zipfile
import json
import os
from pathlib import Path
import re
import secrets
import sys
import urllib.parse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import merge_on_green as mog
contract = mog.proof_admission


PAGE = 'totalCount pageInfo { hasNextPage endCursor }'
COMMENT = '''id fullDatabaseId body createdAt repository { nameWithOwner }
 pullRequest { number } author { __typename login ... on Bot { databaseId } ... on User { databaseId } }'''
RUN = 'id name status'
SUITE = f'''id repository {{ nameWithOwner }} commit {{ oid }} app {{ databaseId slug }} checkRuns(first:100, filterBy:{{checkType:LATEST}}) {{ {PAGE} nodes {{ {RUN} }} }}'''
META = '''number state isDraft headRefOid baseRefOid baseRefName
 repository { nameWithOwner }'''
MERGE = '''potentialMergeCommit { oid parents(first:3) { totalCount pageInfo { hasNextPage endCursor } nodes { oid } }
 file(path:".github/workflows/ci.yml") { path oid type object { __typename ... on Blob { oid byteSize isBinary isTruncated text } } } }'''
RATE = 'rateLimit { cost limit remaining resetAt }'


def positive(value):
    return type(value) is int and value > 0


def decimal_id(value):
    # GraphQL BigInt serializes as a decimal string, unlike REST's integer.
    if positive(value):
        return value
    if isinstance(value, str) and re.fullmatch('[1-9][0-9]*', value):
        return int(value)
    raise ValueError('missing exact server database identity')


def connection(value):
    if (not isinstance(value, dict) or type(value.get('totalCount')) is not int
            or value['totalCount'] < 0 or not isinstance(value.get('nodes'), list)
            or any(not isinstance(n, dict) for n in value['nodes'])):
        raise ValueError('incomplete GraphQL connection')
    page = value.get('pageInfo')
    if (not isinstance(page, dict) or type(page.get('hasNextPage')) is not bool
            or page['hasNextPage'] and (not isinstance(page.get('endCursor'), str) or not page['endCursor'])):
        raise ValueError('incomplete GraphQL pagination')
    return value['nodes'], value['totalCount'], page['endCursor'] if page['hasNextPage'] else None


def comment_row(node, repo, number):
    if (node.get('repository') != {'nameWithOwner': repo}
            or node.get('pullRequest') != {'number': number} or not isinstance(node.get('body'), str)):
        raise ValueError('foreign or malformed comment custody')
    author = node.get('author')
    if not isinstance(author, dict) or author.get('__typename') not in {'Bot', 'User'} or not isinstance(author.get('login'),str):
        raise ValueError('unavailable comment author')
    return dict(id=decimal_id(node.get('fullDatabaseId')), body=node['body'],
                created_at=node.get('createdAt'), user=dict(id=decimal_id(author.get('databaseId')),
                login=author.get('login'), type=author['__typename']))


class BulkReader:
    """Fresh complete connections; pagination is local to this original read.

    Positive CI presence is discovery only. The caller must still obtain the
    original REST/evidence representation before a refresh freshness verdict.
    No GraphQL mutable PR association is converted to a tested proof base.
    """
    def __init__(self, mog, repo, token, *, deadline, clock=time.monotonic):
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo):
            raise ValueError('invalid repository')
        self.mog, self.repo, self.token = mog, repo, token
        self.deadline, self.clock = deadline, clock
        self.owner, self.name = repo.split('/')
        code, data = mog._request('GET', mog.GITHUB_API + '/rate_limit', token)
        quota = (data.get('resources') or {}).get('graphql') if isinstance(data, dict) else None
        if code != 200 or not isinstance(quota, dict) or not positive(quota.get('limit')) or type(quota.get('remaining')) is not int:
            raise ValueError('GraphQL quota unavailable')
        self.remaining, self.limit = quota['remaining'], quota['limit']
        self.queries = 0

    def query(self, body, variables=None, *, nodes=False):
        if self.clock() >= self.deadline or self.remaining < self.mog.RATE_LIMIT_RESERVE + 3:
            raise ValueError('incomplete census at GraphQL budget/deadline boundary')
        query = ('query{' + body + ' ' + RATE + '}' if nodes else
                 'query($owner:String!,$name:String!){ repository(owner:$owner,name:$name){' + body + '} ' + RATE + '}')
        code, response = self.mog._request('POST', self.mog.GITHUB_API + '/graphql', self.token,
            {'query': query, 'variables': {} if nodes else {'owner': self.owner, 'name': self.name, **(variables or {})}})
        self.queries += 1
        if code != 200 or not isinstance(response, dict) or response.get('errors'):
            raise ValueError('partial or unavailable GraphQL census')
        data = response.get('data')
        rate = data.get('rateLimit') if isinstance(data, dict) else None
        if (not isinstance(rate, dict) or not positive(rate.get('cost')) or not positive(rate.get('limit'))
                or type(rate.get('remaining')) is not int or rate['remaining'] < 0
                or not isinstance(rate.get('resetAt'), str) or rate['cost'] > 3):
            raise ValueError('unqualified GraphQL query cost or response')
        self.remaining, self.limit = rate['remaining'], rate['limit']
        headers=self.mog.last_response_headers()
        if headers.get('x-ratelimit-resource')=='graphql':
            try:
                remaining=int(headers['x-ratelimit-remaining']);limit=int(headers['x-ratelimit-limit'])
            except (KeyError,TypeError,ValueError) as exc:
                raise ValueError('GraphQL quota headers incomplete') from exc
            if remaining<0 or limit<=0:raise ValueError('GraphQL quota headers invalid')
            self.remaining,self.limit=remaining,limit
        if self.remaining < self.mog.RATE_LIMIT_RESERVE or self.clock() >= self.deadline:
            raise ValueError('incomplete census after GraphQL budget/deadline boundary')
        if nodes:
            if not isinstance(data.get('nodes'),list):raise ValueError('node read unavailable')
            return data['nodes']
        if not isinstance(data.get('repository'), dict):
            raise ValueError('repository census unavailable')
        return data['repository']

    def all_pages(self, first, fetch, *, maximum):
        rows, total, cursor = connection(first)
        if total > maximum:
            raise ValueError('existing connection census bound exceeded')
        seen_cursors = set()
        while cursor is not None:
            if cursor in seen_cursors:
                raise ValueError('repeated connection cursor')
            seen_cursors.add(cursor)
            more, observed_total, cursor = connection(fetch(cursor))
            if total != observed_total or not more:
                raise ValueError('connection changed or failed to advance')
            rows += more
            if len(rows) > maximum:
                raise ValueError('connection census bound exceeded')
        if len(rows) != total:
            raise ValueError('connection omitted rows')
        ids = [r.get('id') for r in rows]
        if any(not isinstance(v, str) or not v for v in ids) or len(set(ids)) != len(ids):
            raise ValueError('connection duplicate/missing node identity')
        return rows

    def facts(self, pulls):
        result = {}
        if len({p['number'] for p in pulls}) != len(pulls):
            raise ValueError('duplicate PR discovery')
        for start in range(0, len(pulls), 25):
            batch = pulls[start:start+25]
            fields=[]
            for p in batch:
                n=p['number'];head=(p.get('head') or {}).get('sha')
                if not positive(n) or not isinstance(head,str) or not re.fullmatch('[0-9a-f]{40}',head):
                    raise ValueError('invalid original PR identity')
                fields.append(f'p{n}:pullRequest(number:{n}){{ {META} comments(first:100){{ {PAGE} nodes{{ {COMMENT} }} }} {MERGE} }}')
                fields.append(f'h{n}:object(oid:"{head}"){{ __typename ... on Commit{{ oid checkSuites(first:5){{ {PAGE} nodes{{ {SUITE} }} }} }} }}')
            data=self.query(' '.join(fields))
            for p in batch:
                n=p['number'];pr=data.get(f'p{n}');head=data.get(f'h{n}')
                if (not isinstance(pr,dict) or pr.get('number') != n or pr.get('state') != 'OPEN'
                        or pr.get('repository') != {'nameWithOwner':self.repo}
                        or pr.get('headRefOid') != p['head']['sha'] or pr.get('baseRefOid') != p['base']['sha']
                        or pr.get('baseRefName') != p['base']['ref'] or pr.get('isDraft') is not p.get('draft')
                        or not isinstance(head,dict) or head.get('__typename') != 'Commit' or head.get('oid') != p['head']['sha']):
                    raise ValueError('PR changed during complete census')
                def comments_after(cursor):
                    row=self.query(f'p:pullRequest(number:{n}){{ {META} comments(first:100,after:{json.dumps(cursor)}){{ {PAGE} nodes{{ {COMMENT} }} }} }}')['p']
                    if any(row.get(k)!=pr.get(k) for k in ('number','headRefOid','baseRefOid','state','repository')):
                        raise ValueError('PR changed during comment read')
                    return row['comments']
                comments=self.all_pages(pr['comments'],comments_after,maximum=100*self.mog.HOLD_COMMENT_PAGE_CAP)
                def suites_after(cursor):
                    return self.query(f'h:object(oid:"{p["head"]["sha"]}"){{ ... on Commit{{ checkSuites(first:5,after:{json.dumps(cursor)}){{ {PAGE} nodes{{ {SUITE} }} }} }} }}')['h']['checkSuites']
                suites=self.all_pages(head['checkSuites'],suites_after,maximum=100*self.mog.CHECK_RUN_PAGE_CAP)
                ci_present=False
                for suite in suites:
                    if suite.get('repository')!={'nameWithOwner':self.repo} or suite.get('commit')!={'oid':p['head']['sha']}:
                        raise ValueError('foreign check suite source')
                    app=suite.get('app')
                    if not isinstance(app,dict) or not positive(app.get('databaseId')) or not isinstance(app.get('slug'),str):
                        raise ValueError('check suite app provenance unavailable')
                    # Each continuation rebinds to this exact opaque server suite ID.
                    def runs_after(cursor):
                        nodes=self.query(f'nodes(ids:[{json.dumps(suite["id"])}]){{ id ... on CheckSuite{{ checkRuns(first:100,filterBy:{{checkType:LATEST}},after:{json.dumps(cursor)}){{ {PAGE} nodes{{ {RUN} }} }} }} }}',nodes=True)
                        if len(nodes)!=1 or nodes[0].get('id')!=suite['id']:
                            raise ValueError('foreign check suite continuation')
                        return nodes[0]['checkRuns']
                    runs=self.all_pages(suite['checkRuns'],runs_after,maximum=100*self.mog.CHECK_RUN_PAGE_CAP)
                    for run in runs:
                        if not isinstance(run.get('name'),str) or run.get('status') not in {'COMPLETED','IN_PROGRESS','PENDING','QUEUED','REQUESTED','WAITING'}:
                            raise ValueError('check run state unavailable')
                        if app['slug']=='github-actions' and run['name'] in self.mog.REQUIRED_CI_ANCHORS | {self.mog.REQUIRED_CI_GATE}:
                            ci_present=True
                native=self.native(pr.get('potentialMergeCommit'),p)
                result[n]=dict(comments=[comment_row(c,self.repo,n) for c in comments], ci_present=ci_present, native=native)
        return result

    @staticmethod
    def native(merge,pull):
        if merge is None:
            return None
        if not isinstance(merge,dict) or merge.get('oid') != pull.get('merge_commit_sha'):
            raise ValueError('candidate merge changed')
        parents=merge.get('parents');rows,total,cursor=connection(parents)
        if total!=2 or cursor is not None or [r.get('oid') for r in rows] != [pull['base']['sha'],pull['head']['sha']]:
            return None
        entry=merge.get('file');blob=entry.get('object') if isinstance(entry,dict) else None
        if (not isinstance(entry,dict) or entry.get('path')!='.github/workflows/ci.yml' or entry.get('type')!='blob'
                or not isinstance(blob,dict) or blob.get('__typename')!='Blob' or blob.get('oid')!=entry.get('oid')
                or blob.get('isBinary') is not False or blob.get('isTruncated') is not False
                or not isinstance(blob.get('text'),str) or type(blob.get('byteSize')) is not int
                or not 0<blob['byteSize']<=1048576 or len(blob['text'].encode())!=blob['byteSize']
                or hashlib.sha1(b'blob '+str(blob['byteSize']).encode()+b'\0'+blob['text'].encode()).hexdigest()!=blob['oid']):
            raise ValueError('candidate workflow bytes incomplete')
        import yaml
        class UniqueLoader(yaml.SafeLoader):pass
        def unique(loader,node,deep=False):
            result={}
            for key_node,value_node in node.value:
                key=loader.construct_object(key_node,deep=deep)
                if key in result:raise ValueError('duplicate candidate workflow key')
                result[key]=loader.construct_object(value_node,deep=deep)
            return result
        UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,unique)
        document=yaml.load(blob['text'],Loader=UniqueLoader)
        if not isinstance(document,dict):raise ValueError('candidate workflow malformed')
        events=document.get('on',document.get(True))
        if isinstance(events,str):return events=='pull_request'
        if isinstance(events,(dict,list)):return 'pull_request' in events
        raise ValueError('candidate entrypoint unavailable')


@dataclass(frozen=True)
class IndexState:
    artifact: int
    anchor: int
    intent: int = 0
    not_before: int = 0

    def text(self):
        return f'a2 b={self.artifact} p={self.anchor} i={self.intent} t={self.not_before} s=indexing'

    @classmethod
    def parse(cls, value):
        match=re.fullmatch(r'a2 b=([1-9][0-9]*) p=([1-9][0-9]*) i=(0|[1-9][0-9]*) t=([0-9]+) s=indexing',str(value))
        if not match:return None
        return cls(*(int(v) for v in match.groups()))


class AnchorIndexer:
    """One original demand artifact, per-PR comments, incumbent a2 custody.

    Indexing state is NOT a launch or a workload reservation. The incumbent
    inventory/complete/cleanup adapters must recognize it and retain it until
    this protocol positively finishes. No partial result authorizes selection.
    """
    def __init__(self, mog, repo, job_token, context, *, deadline, clock=time.time, sleep=time.sleep):
        self.mog,self.repo,self.token,self.context=mog,repo,job_token,context
        self.deadline,self.clock,self.sleep=deadline,clock,sleep
        self.root=mog.GITHUB_API+'/repos/'+repo
        self.label=self.root+'/labels/'+urllib.parse.quote(mog.REFRESH_LEASE_LABEL,safe='')

    def authority(self):
        if not self.mog._shared_controller_authority(self.repo,self.token,**self.context):
            raise ValueError('not the original protected serialized controller')

    def read(self):
        code,row=self.mog._request('GET',self.label,self.token)
        if code!=200 or not isinstance(row,dict):raise ValueError('index custody unreadable')
        return row.get('description')

    def wait_write(self,state):
        # At most one content mutation per ten seconds in this retained protocol:
        # 360/hour, below documented80/min and500/hour. Other writers can consume
        # the shared allowance; a provider refusal is never assumed harmless.
        delay=max(0,state.not_before-self.clock())
        if self.clock()+delay+1>=self.deadline:return False
        if delay:self.sleep(delay)
        return True

    def store(self,state):
        code,_=self.mog._request('PATCH',self.label,self.token,{'description':state.text()})
        if code!=200 or self.read()!=state.text():raise RuntimeError('UNKNOWN original indexing custody write')
        return state

    def authenticate(self,state):
        """Label is discovery only. Authenticate original Actions bytes/ancestry."""
        code,artifact=self.mog._request('GET',self.root+f'/actions/artifacts/{state.artifact}',self.token)
        if code!=200 or not isinstance(artifact,dict):raise ValueError('original batch unavailable')
        name=re.fullmatch(r'ci-proof-demands-([1-9][0-9]*)-([1-9][0-9]*)',str(artifact.get('name')))
        binding=artifact.get('workflow_run') or {}
        control=binding.get('head_sha')
        if not name or not isinstance(control,str) or not re.fullmatch('[0-9a-f]{40}',control):
            raise ValueError('batch controller identity unavailable')
        current=self.context['protected_controller_sha']
        if control!=current:
            code,ancestry=self.mog._request('GET',self.root+f'/compare/{control}...{current}?per_page=1',self.token)
            if (code!=200 or not isinstance(ancestry,dict) or ancestry.get('status') not in {'identical','ahead'}
                    or (ancestry.get('base_commit') or {}).get('sha')!=control
                    or (ancestry.get('merge_base_commit') or {}).get('sha')!=control):
                raise ValueError('batch not protected control ancestry')
        run,attempt=map(int,name.groups())
        code,controller=self.mog._request('GET',self.root+f'/actions/runs/{run}/attempts/{attempt}',self.token)
        if code!=200:raise ValueError('original batch attempt unavailable')
        archive=self.mog._download_semantic_artifact(self.root+f'/actions/artifacts/{state.artifact}/zip',self.token)
        # Derive a locator from exactly the bounded downloaded member. It grants
        # no trust: authenticate_demands verifies archive server digest, source,
        # original attempt, canonical single member, schema and every demand.
        if not isinstance(archive,bytes) or len(archive)>1048576:raise ValueError('invalid batch archive')
        with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
            members=bundle.infolist()
            if len(members)!=1 or members[0].filename!='ci-proof-admission.json' or members[0].file_size>262144:
                raise ValueError('ambiguous batch archive')
            payload=bundle.read(members[0])
        digest=hashlib.sha256(payload).hexdigest()
        ref=dict(artifact_id=state.artifact,controller_run_id=run,controller_attempt=attempt,controller_sha=control,payload_sha256=digest)
        snapshot=self.mog.proof_admission.authenticate_age_snapshot(archive=archive,payload_sha256=digest,
            repository_id=self.context['repository_id'],artifact_id=state.artifact,controller_run_id=run,
            controller_attempt=attempt,controller_sha=control,artifact=artifact,controller=controller)
        self.authenticated_snapshot=snapshot
        demands=list(snapshot.demands)
        numbers={d.pr_number for d in demands}
        if (state.intent==3 and state.anchor not in dict(snapshot.covered_comments) or state.intent!=3 and state.anchor not in numbers) or state.intent not in {0, 1, 2, 3}:
            raise ValueError('index pointer not in authenticated original batch')
        return ref,demands

    def start(self,artifact_id,anchor):
        self.authority()
        if self.read()!='a2 idle':raise ValueError('original singleton occupied')
        state=IndexState(artifact_id,anchor,not_before=int(self.clock())+10)
        self.authenticate(state)
        if self.clock()+1>=self.deadline:return {'disposition':'deferred'}
        self.store(state)  # Durable artifact discovery precedes the first POST.
        return {'disposition':'indexing','state':state}

    def exact_comment(self,number,body,comments):
        matching=[]
        for c in comments:
            if not isinstance(c,dict):raise ValueError('incomplete original comments')
            if c.get('body')==body and self.mog.admission_index_writer(c):
                if not positive(c.get('id')):raise ValueError('missing original comment ID')
                matching.append(c)
        if len(matching)>1:raise RuntimeError('UNKNOWN duplicate original index')
        if not matching:return None
        c=matching[0]
        snapshot=getattr(self,'authenticated_snapshot',None)
        if snapshot is not None and any(cutoff>=c['id'] for _,cutoff in snapshot.covered_comments):
            raise ValueError('original age index is inside its own/future coverage')
        code,observed=self.mog._request('GET',self.root+f'/issues/comments/{c["id"]}',self.token)
        if (code!=200 or not isinstance(observed,dict) or observed.get('id')!=c['id']
                or observed.get('body')!=body or not self.mog.admission_index_writer(observed)):
            raise RuntimeError('UNKNOWN original comment readback')
        return c

    def advance(self):
        """Finish only the original anchor comment/association; never select."""
        from dataclasses import replace
        self.authority()
        state=IndexState.parse(self.read())
        if state is None:raise ValueError('no original indexing batch')
        ref,demands=self.authenticate(state)
        if state.intent==3:
            url=self.root+f'/issues/{state.anchor}/labels'
            code,labels=self.mog._request('GET',url,self.token)
            if code!=200 or not isinstance(labels,list):raise ValueError('retirement readback unknown')
            if any(isinstance(v,dict) and v.get('name')==self.mog.REFRESH_LEASE_LABEL for v in labels):
                return {'disposition':'unknown','detail':'original retirement not positively observed'}
            if not self.wait_write(state):return {'disposition':'partial'}
            code,_=self.mog._request('PATCH',self.label,self.token,{'description':'a2 idle'})
            if code!=200 or self.read()!='a2 idle':raise RuntimeError('UNKNOWN retirement finalization')
            return {'disposition':'indexed','artifact_id':state.artifact,'anchor':state.anchor}
        body=self.mog.DEMAND_COMMENT_PREFIX+json.dumps(ref,sort_keys=True,separators=(',',':'))
        comments=self.mog.fetch_issue_comments(self.repo,state.anchor,self.token,strict=True)
        if comments is None:raise ValueError('original anchor comments incomplete')
        original=self.exact_comment(state.anchor,body,comments)
        if state.intent and original is None:
            return {'disposition':'unknown','detail':'original anchor POST not positively found'}
        if original is None:
            # Do not write an intent if this original call lacks time to POST
            # and read back. A crash after intent still remains UNKNOWN.
            if max(self.clock(),state.not_before)+31>=self.deadline:
                return {'disposition':'partial'}
            if not self.wait_write(state):return {'disposition':'partial'}
            state=self.store(replace(state,intent=1,not_before=int(self.clock())+10))
            if not self.wait_write(state):return {'disposition':'partial'}
            try:
                code,c=self.mog._request('POST',self.root+f'/issues/{state.anchor}/comments',self.token,{'body':body})
            except Exception:
                return {'disposition':'unknown','detail':'original anchor POST response lost'}
            if code!=201 or not isinstance(c,dict) or self.exact_comment(state.anchor,body,[c]) is None:
                return {'disposition':'unknown','detail':'original anchor POST not positively read back'}
            state=replace(state,not_before=int(self.clock())+10)
        # Positive label readback is required even if the anchor closed. Phase2
        # records the association POST intent; its absence never authorizes retry.
        url=self.root+f'/issues/{state.anchor}/labels'
        code,labels=self.mog._request('GET',url,self.token)
        if code!=200 or not isinstance(labels,list):raise ValueError('anchor association unavailable')
        present=any(isinstance(v,dict) and v.get('name')==self.mog.REFRESH_LEASE_LABEL for v in labels)
        if not present:
            if state.intent==2:return {'disposition':'unknown','detail':'original anchor association not positively found'}
            if max(self.clock(),state.not_before)+31>=self.deadline:return {'disposition':'partial'}
            if not self.wait_write(state):return {'disposition':'partial'}
            state=self.store(replace(state,intent=2,not_before=int(self.clock())+10))
            if not self.wait_write(state):return {'disposition':'partial'}
            try:
                code,_=self.mog._request('POST',url,self.token,{'labels':[self.mog.REFRESH_LEASE_LABEL]})
                status,labels=self.mog._request('GET',url,self.token)
            except Exception:
                return {'disposition':'unknown','detail':'original association response lost'}
            if code!=200 or status!=200 or not isinstance(labels,list) or not any(isinstance(v,dict) and v.get('name')==self.mog.REFRESH_LEASE_LABEL for v in labels):
                return {'disposition':'unknown','detail':'original association readback unsettled'}
            state=replace(state,not_before=int(self.clock())+10)
        if not self.wait_write(state):return {'disposition':'partial'}
        code,_=self.mog._request('PATCH',self.label,self.token,{'description':'a2 idle'})
        if code!=200 or self.read()!='a2 idle':raise RuntimeError('UNKNOWN indexing finalization')
        return {'disposition':'indexed','artifact_id':state.artifact,'anchor':state.anchor}

    def retire_covered_anchor(self,new_reference):
        self.authority()
        if self.read()!='a2 idle':return {'disposition':'held'}
        inventory=self.mog.shared_admission_inventory(self.repo,self.token)
        snapshot,_=self.mog.read_age_frontier(self.repo,self.token,
            repository_id=self.context['repository_id'],protected_controller_sha=self.context['protected_controller_sha'],inventory=inventory)
        coverage=dict(snapshot.covered_comments)
        workload=self.mog.shared_proof_workload(self.repo,self.token,
            repository_id=self.context['repository_id'],protected_controller_sha=self.context['protected_controller_sha'],age_snapshot=snapshot)
        if not workload.complete or inventory.launch is not None or inventory.indexing is not None:
            return {'disposition':'held'}
        for issue in inventory.issues:
            number=issue['number']
            if number not in coverage:continue
            if any(a.pr_number==number and not a.settled for a in workload.admissions):continue
            comments=self.mog.fetch_issue_comments(self.repo,number,self.token,strict=True)
            if comments is None:raise ValueError('retirement coverage incomplete')
            originals=[c for c in comments if isinstance(c.get('body'),str)
                and c['body'].startswith(self.mog.DEMAND_COMMENT_PREFIX) and self.mog.admission_index_writer(c)]
            if not originals or any(not positive(c.get('id')) or c['id']>coverage[number] for c in originals):continue
            # All age indexes on this association are explicitly covered by the
            # authenticated successor. Other PR admission records stay intact.
            if self.clock()+31>=self.deadline:return {'disposition':'partial'}
            self.sleep(10)
            state=IndexState(new_reference['artifact_id'],number,3,int(self.clock())+10)
            actual,_=self.authenticate(state)
            if actual!=new_reference:raise ValueError('retirement successor reference mismatch')
            self.store(state)
            if not self.wait_write(state):return {'disposition':'partial'}
            url=self.root+f'/issues/{number}/labels/'+urllib.parse.quote(self.mog.REFRESH_LEASE_LABEL,safe='')
            try:code,_=self.mog._request('DELETE',url,self.token)
            except Exception:return {'disposition':'unknown','detail':'original retirement response lost'}
            if code not in {200,204}:return {'disposition':'unknown','detail':'original retirement unresolved'}
            state=IndexState(state.artifact,state.anchor,state.intent,int(self.clock())+10)
            # advance performs readback only; even a missing DELETE response
            # can never cause a second DELETE on a future sweep.
            self.sleep(10)
            return self.advance()
        return {'disposition':'retained'}


def conserve_age_witnesses(old_demands, replacement, pulls, admissions):
    """A replacement may retire only known closed or admitted generations.

    Inputs are exact resolved prior identities and authenticated receipt reads. This
    check grants no deletion or selection; the caller still reconciles custody.
    """
    observed_prs={p['number']:p for p in pulls}
    expected=[]
    for number in sorted({d.pr_number for d in old_demands}):
        originals=[d for d in old_demands if d.pr_number==number]
        # Exact authenticated admission consumes a generation even when its PR
        # cannot be observed. Absence from mutable discovery never does.
        pending=contract.pending_demand_for_pr(originals,admissions,number,originals[-1].head_sha)
        if pending is None:continue
        row=observed_prs.get(number)
        if row is None or row.get('state') not in {'open','closed'}:
            raise ValueError('unresolved prior pending witness')
        if row['state']=='closed':continue
        expected.append(contract.replace_pending_head(pending,row['head']['sha']))
    observed={d.pr_number:d for d in contract.ordered_demands(replacement)}
    if any(observed.get(d.pr_number)!=d for d in expected):
        raise ValueError('replacement lost or rewrote an unserved original age witness')


def write_once(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, sort_keys=True, separators=(',', ':')).encode()
    with path.open('xb') as out:
        out.write(payload)
    return hashlib.sha256(payload).hexdigest()


class Stages:
    def __init__(self, repo, read_token, write_token, checks_token, context, directory):
        self.repo, self.read, self.write, self.checks = repo, read_token, write_token, checks_token
        self.context = context
        self.directory = Path(directory)

    def authority(self):
        if not mog._shared_controller_authority(self.repo, self.read, **self.context):
            raise ValueError('not exact protected serialized original controller')

    def save(self, name, data):
        return write_once(self.directory / (name + '.json'), data)

    def load(self, name):
        return json.loads((self.directory / (name + '.json')).read_text(),
                          object_pairs_hook=contract._unique_object)

    def emit_decision(self, stage, **evidence):
        """Original controller log evidence; never a receipt or admission input."""
        print(json.dumps(dict(admission_decision=stage,
            controller_run_id=int(self.context['current_run_id']),
            controller_run_attempt=self.context['current_run_attempt'],
            controller_sha=self.context['protected_controller_sha'], **evidence),
            sort_keys=True), flush=True)

    def receipt(self, kind, value, suffix, *, covered_comments=None):
        schema = {'admission': 'mastermind.ci-proof-admission.v1',
                  'demands': 'mastermind.ci-proof-demands.v1',
                  'checkpoint': 'mastermind.ci-proof-checkpoint.v1'}[kind]
        data = dict(schema=schema, repository_id=self.context['repository_id'],
                    controller_run_id=int(self.context['current_run_id']),
                    controller_run_attempt=self.context['current_run_attempt'])
        data[kind] = value
        if kind=='demands' and covered_comments is not None:
            data['schema']='mastermind.ci-proof-demands.v2'
            data['covered_comments']=[dict(pr_number=n,through_comment_id=c) for n,c in sorted(covered_comments.items())]
            if len(data['covered_comments'])>1000:raise ValueError('existing age coverage bound exceeded')
        digest = write_once(self.directory / suffix / 'ci-proof-admission.json', data)
        self.save(suffix + '-digest', digest)

    def reference(self, suffix, artifact_id):
        if type(artifact_id) is not int or artifact_id <= 0:
            raise ValueError('no original upload artifact identity')
        return dict(artifact_id=artifact_id,
                    controller_run_id=int(self.context['current_run_id']),
                    controller_attempt=self.context['current_run_attempt'],
                    controller_sha=self.context['protected_controller_sha'],
                    payload_sha256=self.load(suffix + '-digest'))

    def initialize_empty_register(self):
        """Only a positively idle legacy register with no owners may migrate."""
        root = f'{mog.GITHUB_API}/repos/{self.repo}'
        url = root + '/labels/' + urllib.parse.quote(mog.REFRESH_LEASE_LABEL, safe='')
        status, label = mog._request('GET', url, self.read)
        if status == 200 and isinstance(label, dict) and str(label.get('description', '')).startswith('a2 '):
            return
        if status != 200 or not isinstance(label, dict) or label.get('description') != mog.REFRESH_LEASE_DESCRIPTION:
            raise ValueError('legacy register missing, occupied or unknown; no migration')
        # Complete state=all associations, not just the open queue. An old m1
        # association is never interpreted as empty because its PR closed.
        query = urllib.parse.urlencode(dict(state='all', labels=mog.REFRESH_LEASE_LABEL, per_page=100))
        code, rows = mog._request('GET', root + '/issues?' + query, self.read)
        if code != 200 or rows != []:
            raise ValueError('legacy owner association remains; no migration')
        code, _ = mog._request('PATCH', url, self.write, {'description': 'a2 idle'})
        if code != 200:
            raise RuntimeError('UNKNOWN original register migration')
        code, observed = mog._request('GET', url, self.read)
        if code != 200 or not isinstance(observed, dict) or observed.get('description') != 'a2 idle':
            raise RuntimeError('UNKNOWN original register migration readback')

    def history(self, pull, comments=None):
        if comments is None:
            comments = mog.fetch_issue_comments(self.repo, pull['number'], self.read, strict=True)
        if comments is None:
            raise ValueError('incomplete original PR comments')
        prefixes = (mog.ADMISSION_COMMENT_PREFIX, mog.DEMAND_COMMENT_PREFIX, mog.CHECKPOINT_COMMENT_PREFIX)
        if not any(str(c.get('body', '')).startswith(prefixes) for c in comments):
            if mog.REFRESH_LEASE_LABEL in mog.label_names(pull):
                raise ValueError('associated PR lacks original receipt')
            return [], []
        return mog.pr_admission_history(self.repo, self.read, pull['number'], comments,
            repository_id=self.context['repository_id'],
            protected_controller_sha=self.context['protected_controller_sha'],
            allow_empty=mog.REFRESH_LEASE_LABEL not in mog.label_names(pull),
            age_snapshot=getattr(self,"_age_snapshot",None))

    def anchor_indexer(self):
        return AnchorIndexer(mog,self.repo,self.read,self.context,deadline=time.time()+240)

    def age_witnesses(self, inventory, facts):
        retention={}
        snapshot,coverage=mog.read_age_frontier(self.repo,self.read,
            repository_id=self.context['repository_id'],protected_controller_sha=self.context['protected_controller_sha'],
            inventory=inventory,comments_by_pr={n:f['comments'] for n,f in facts.items()},retention=retention)
        expiry=retention['earliest_expiry']
        # Renew in the last day of actual server retention, while every
        # uncovered predecessor is still authenticated. This is an upload
        # scheduling margin, never a TTL waiver or a new demand-age clock.
        self._age_renewal_due=(expiry is not None and
            datetime.fromisoformat(expiry).timestamp()-datetime.now(timezone.utc).timestamp()<=86400)
        self._age_snapshot=snapshot
        self._age_coverage=coverage
        return list(snapshot.demands)

    def candidate_native_entrypoint(self, pull):
        import base64
        import yaml
        merge = pull.get('merge_commit_sha')
        if not isinstance(merge, str) or not re.fullmatch('[0-9a-f]{40}', merge):
            return None
        root = f'{mog.GITHUB_API}/repos/{self.repo}'
        code, commit = mog._request('GET', root + f'/git/commits/{merge}', self.read)
        if (code != 200 or not isinstance(commit, dict) or commit.get('sha') != merge
                or [p.get('sha') for p in commit.get('parents', [])] !=
                   [(pull.get('base') or {}).get('sha'), (pull.get('head') or {}).get('sha')]):
            return None
        code, data = mog._request('GET', root + '/contents/.github/workflows/ci.yml?ref=' + merge, self.read)
        if (code != 200 or not isinstance(data, dict) or data.get('type') != 'file'
                or data.get('encoding') != 'base64' or type(data.get('size')) is not int
                or not 0 < data['size'] <= 1048576):
            raise ValueError('candidate CI entrypoint unavailable')
        raw = base64.b64decode(''.join(data['content'].split()), validate=True)
        if len(raw) != data['size']:
            raise ValueError('candidate CI entrypoint truncated')
        workflow = yaml.safe_load(raw)
        if not isinstance(workflow, dict):
            raise ValueError('candidate CI entrypoint malformed')
        events = workflow.get('on', workflow.get(True))
        if isinstance(events, str):
            return events == 'pull_request'
        if isinstance(events, (dict, list)):
            return 'pull_request' in events
        raise ValueError('candidate CI entrypoints unknown')

    def demand_evaluation(self, pull, runs, freshness, native_pr_enabled, *, expected_ci=False):
        """Current eligibility, distinct from unavailable original proof facts."""
        anchors = mog.proof_anchor_runs(runs)
        ci = [v for k, v in anchors.items() if k in {'ci-plan', 'contract-delta', 'ci-gate'} or k.startswith('ci-pack')]
        if any(r.get('status') not in contract.ACTIVE_STATUSES | {'completed'} for r in ci):
            return 'unknown', None
        if any(r.get('status') != 'completed' for r in ci):
            return 'ineligible', None
        if not ci and expected_ci:
            return 'unknown', None  # fresh REST contradicts advertised original CI
        if not ci:
            return ('ineligible', None) if native_pr_enabled else ('eligible', 'authored')
        if not mog.is_sweep_candidate(pull):
            return 'ineligible', None
        if freshness is None:
            return 'unknown', None
        stale, _reason = freshness.stale_for(pull, runs)
        if stale is None:
            return 'unknown', None
        return ('eligible', 'refresh') if stale is True else ('ineligible', None)

    def prepare(self, *, native_pr_enabled, freshness):
        self.authority()
        # Readiness is the actual protected caller/callee contract, not a flag
        # or candidate claim. Foundation installation must not migrate the
        # legacy register or create demand before the bridge is installed.
        if not mog.installed_admitted_dispatch_ready(
                self.repo, self.context['protected_controller_sha']):
            return dict(ready=False, changed=False, count=0)
        self.initialize_empty_register()
        inventory=mog.shared_admission_inventory(self.repo,self.read)
        if not inventory.complete:raise ValueError('incomplete original custody inventory')
        if inventory.indexing is not None:
            self.save('resume-index',list(inventory.indexing))
            return dict(ready=True,changed=False,count=0)
        budget = mog.SweepBudget(self.read)
        if not budget.preflight()[0]:
            raise ValueError('insufficient original budget for complete demand census')
        pulls = mog.open_pulls(self.repo, self.read)
        deadline=time.monotonic()+300
        reader=BulkReader(mog,self.repo,self.read,deadline=deadline)
        facts=reader.facts(pulls)
        ages=self.age_witnesses(inventory,facts)
        workload = mog.shared_proof_workload(self.repo, self.read,
            repository_id=self.context['repository_id'],
            protected_controller_sha=self.context['protected_controller_sha'],age_snapshot=self._age_snapshot)
        if not workload.complete:
            raise ValueError('incomplete shared workload')
        # The state=all association inventory is controlled by this serialized
        # writer, independently of mutable state=open discovery. Include pending
        # checkpoint/history witnesses already authenticated by the workload read.
        ages=[*ages,*workload.demands]
        resolved={p['number']:p for p in pulls}
        prior_numbers={d.pr_number for d in ages}
        if len(set(resolved)|prior_numbers)>mog.OPEN_PULL_PAGE_CAP*100:
            raise ValueError('prior witness/discovery union exceeds existing bound')
        recovered=[]
        for index,number in enumerate(sorted(prior_numbers-set(resolved))):
            originals=[d for d in ages if d.pr_number==number]
            pending=contract.pending_demand_for_pr(originals,workload.admissions,number,originals[-1].head_sha)
            if pending is None:continue
            if time.monotonic()>=deadline or not budget.may_continue(index)[0]:
                raise ValueError('unresolved prior witness at budget/deadline boundary')
            code,row=mog._request('GET',f'{mog.GITHUB_API}/repos/{self.repo}/pulls/{number}',self.read)
            if (code!=200 or not isinstance(row,dict) or type(row.get('number')) is not int
                    or row['number']!=number or row.get('state') not in {'open','closed'}
                    or type(((row.get('base') or {}).get('repo') or {}).get('id')) is not int
                    or ((row.get('base') or {}).get('repo') or {}).get('id')!=self.context['repository_id']
                    or not isinstance((row.get('head') or {}).get('sha'),str)
                    or not re.fullmatch('[0-9a-f]{40}',row['head']['sha'])
                    or time.monotonic()>=deadline):
                raise ValueError('unresolved prior witness identity or state')
            resolved[number]=row
            if row['state']=='open':recovered.append(row)
        # Recovered open subjects get the same current source/merge/comment
        # validation as listed subjects, within the original reader deadline.
        facts.update(reader.facts(recovered))
        pulls=[*pulls,*recovered]
        # Complete age/history custody precedes any bounded eligibility window.
        # Ages order evaluation; they never supply a cached freshness verdict.
        subjects = {}
        history_reads = 0
        for pull in pulls:
            comments = facts[pull['number']]['comments']
            # Empty/non-ledger histories perform no API reads. Poll the existing
            # budget only for histories that can authenticate original receipts.
            if any(str(c.get('body', '')).startswith((mog.ADMISSION_COMMENT_PREFIX,
                    mog.DEMAND_COMMENT_PREFIX, mog.CHECKPOINT_COMMENT_PREFIX)) for c in comments):
                if not budget.may_continue(history_reads)[0]:
                    raise ValueError('incomplete original demand history at budget boundary')
                history_reads += 1
            if pull.get('state') != 'open' or (pull.get('base') or {}).get('ref') != 'main':
                raise ValueError('incomplete open PR census identity')
            head = (pull.get('head') or {}).get('sha')
            if not isinstance(head, str) or not re.fullmatch('[0-9a-f]{40}', head):
                raise ValueError('incomplete open PR identity')
            own = [a for a in workload.admissions if a.pr_number == pull['number']]
            records, prior = self.history(pull, comments)
            prior = prior + [d for d in ages if d.pr_number == pull['number']]
            pending = contract.pending_demand_for_pr(prior, [*records, *own], pull['number'], head)
            subjects[pull['number']] = (pull, own, prior, pending)
        pending = contract.ordered_demands(row[3] for row in subjects.values() if row[3] is not None)
        now = datetime.now(timezone.utc).isoformat()
        learned, changed, evaluated = [], [], []
        stopped = False
        prefix = None
        unknown = False

        def evaluate(number):
            pull, own, prior, old = subjects[number]
            head = pull['head']['sha']
            fact = facts[number]
            if any(not a.settled for a in own) or any(
                    a.head_sha == head and a.base_sha == self.context['protected_controller_sha'] for a in own):
                return 'ineligible', None
            if fact['ci_present'] and not mog.is_sweep_candidate(pull):
                return 'ineligible', None
            if fact['native'] is None:
                return 'unknown', None
            runs = mog.head_check_runs(self.repo, head, self.read) if fact['ci_present'] else []
            state, kind = self.demand_evaluation(pull, runs, freshness, fact['native'], expected_ci=fact['ci_present'])
            if state != 'eligible':
                return state, None
            if kind == 'authored' and any(a.head_sha == head for a in own):
                return 'ineligible', None
            demand = old or contract.Demand(number, head, kind, now, secrets.token_hex(6))
            learned.append(demand)
            if demand not in prior:
                changed.append(demand)
            return state, demand

        # Every new same-original demand is learning-only: mutable discovery
        # cannot certify an exhaustive population, even when all observed rows pass.
        # Existing-proof prefixes need not reread every later original before
        # learning previously unregistered candidates within the SAME budget.
        costly = any(facts[d.pr_number]['ci_present'] for d in pending)
        for demand in pending:
            if not budget.may_continue(len(evaluated))[0]:
                stopped = True
                break
            state, current = evaluate(demand.pr_number)
            evaluated.append(dict(pr_number=demand.pr_number, disposition=state))
            if state == 'unknown':
                unknown = True
                break  # Never overtake an unresolved older registered demand.
            if current is not None and prefix is None:
                prefix = current
                if costly and contract._demand_time(current) < datetime.fromisoformat(now):
                    break
        # Partial learning may publish conserved ages, but NEVER grants a new
        # same-original selection: all new ages share now and random IDs break ties.
        for number, row in subjects.items():
            if row[3] is not None:
                continue
            if not budget.may_continue(len(evaluated))[0]:
                stopped = True
                break
            state, _current = evaluate(number)
            evaluated.append(dict(pr_number=number, disposition=state))
            unknown = unknown or state == 'unknown'
        observed_complete = len(evaluated) == len(subjects) and not stopped and not unknown
        complete = False  # Offset traversal never establishes global completeness.
        # A prior-original rank is before every possible as-yet-unregistered
        # demand only under a STRICT clock comparison. No clock repair or new rank.
        earlier_unknown = any(row['disposition'] == 'unknown' for row in evaluated[:
            next((i for i, row in enumerate(evaluated) if prefix is not None and row['pr_number'] == prefix.pr_number), len(evaluated))])
        prefix_complete = (prefix is not None and not earlier_unknown
            and contract._demand_time(prefix) < datetime.fromisoformat(now))
        # Only this prior-original prefix can authorize the next reservation.
        # The rest of the learned ages belong solely to the conserved receipt.
        demands = [prefix] if prefix_complete else []
        eligibility = dict(complete=complete, discovery_complete=False,
            observed_complete=observed_complete, prior_witnesses_resolved=True, prefix_complete=prefix_complete,
            evaluated=evaluated, unresolved_pr_numbers=sorted((set(subjects)-{r['pr_number'] for r in evaluated})
                | {r['pr_number'] for r in evaluated if r['disposition']=='unknown'}),
            new_demand_time=now, selected_rank=(dict(requested_at=prefix.requested_at,
                demand_id=prefix.demand_id, pr_number=prefix.pr_number) if not complete and prefix_complete else None))
        self.save('census', dict(context=self.context, pulls=pulls,
            demands=[asdict(d) for d in demands], eligibility=eligibility))
        publish_demands = bool(changed)
        if changed or self._age_renewal_due:
            witnesses = {d.pr_number: d for d in learned}
            for demand in pending:
                witnesses.setdefault(demand.pr_number, demand)
            carried = contract.ordered_demands(witnesses.values())
            conserve_age_witnesses(ages, carried, list(resolved.values()), workload.admissions)
            if carried:
                self.receipt('demands', [asdict(d) for d in carried], 'demands', covered_comments=self._age_coverage)
                publish_demands = True
        return dict(ready=True, changed=publish_demands, count=len(demands))

    def index(self, number, prefix, reference):
        if prefix not in {mog.DEMAND_COMMENT_PREFIX, mog.ADMISSION_COMMENT_PREFIX,
                          mog.CHECKPOINT_COMMENT_PREFIX}:
            raise ValueError('unrecognized original receipt namespace')
        body = prefix + json.dumps(reference, sort_keys=True, separators=(',', ':'))
        root = f'{mog.GITHUB_API}/repos/{self.repo}'
        code, result = mog._request('POST', root + f'/issues/{number}/comments', self.read, {'body': body})
        if code != 201 or not isinstance(result, dict) or type(result.get('id')) is not int or result.get('body') != body or not mog.admission_index_writer(result):
            raise RuntimeError('UNKNOWN original receipt index')
        code, observed = mog._request('GET', root + f"/issues/comments/{result['id']}", self.read)
        if code != 200 or observed.get('id') != result['id'] or observed.get('body') != body or not mog.admission_index_writer(observed):
            raise RuntimeError('UNKNOWN original receipt index readback')
        # An unserved demand is recoverable through the complete open-PR census,
        # not yet an admitted capacity lease. Label association here would
        # falsely mark every pending PR as in-flight and exhaust the finite
        # shared owner inventory before any proof slot has been reserved.
        if prefix == mog.DEMAND_COMMENT_PREFIX:
            return
        code, _ = mog._request('POST', root + f'/issues/{number}/labels', self.write, {'labels': [mog.REFRESH_LEASE_LABEL]})
        if code != 200:
            raise RuntimeError('UNKNOWN original receipt association')
        code, observed = mog._request('GET', root + f'/issues/{number}/labels', self.read)
        if code != 200 or not isinstance(observed, list) or mog.REFRESH_LEASE_LABEL not in {x.get('name') for x in observed if isinstance(x, dict)}:
            raise RuntimeError('UNKNOWN original receipt association readback')

    def reserve(self, demand_artifact_id=None):
        self.authority()
        if (self.directory/'resume-index.json').exists():
            outcome=self.anchor_indexer().advance()
            # Even a reconciled original batch waits for a NEW complete current
            # census before any selection. No old partial census is resumed.
            return dict(prepared=False,disposition=outcome['disposition'])
        census = self.load('census')
        if census['context'] != self.context:
            raise ValueError('foreign controller census')
        if (self.directory / 'demands-digest.json').exists():
            ref = self.reference('demands', demand_artifact_id)
            changed = mog.authenticated_demands_from_ref(self.repo, self.read, ref,
                repository_id=self.context['repository_id'], protected_controller_sha=self.context['protected_controller_sha'])
            anchor=changed[0].pr_number
            indexer=self.anchor_indexer()
            indexer.start(ref['artifact_id'],anchor)
            outcome=indexer.advance()
            if outcome['disposition']!='indexed':
                return dict(prepared=False,disposition=outcome['disposition'])
            retirement=indexer.retire_covered_anchor(ref)
            if retirement['disposition'] in {'unknown','partial','held'}:
                return dict(prepared=False,disposition=retirement['disposition'])
        demands = contract.ordered_demands(contract.Demand(**d) for d in census['demands'])
        eligibility = census.get('eligibility', {'complete': True, 'prefix_complete': False})
        if not eligibility['complete'] and not eligibility['prefix_complete']:
            if demands:
                raise ValueError('incomplete eligibility has no selectable prefix')
        self.emit_decision('ordered_demands', census_complete=eligibility['complete'],
            discovery_complete=False, eligibility_prefix_complete=eligibility['prefix_complete'],
            eligibility=eligibility,
            eligibility_phase='prepare', live_eligibility_recheck_required=True,
            ordered_demands=[asdict(d) for d in demands])
        for demand in demands:
            decision = {}
            result = mog.reserve_shared_admission(self.repo, self.read, self.write, demand,
                                                  decision=decision, **self.context)
            self.emit_decision('reservation', demand=asdict(demand),
                disposition=result.disposition, detail=result.detail, decision=decision,
                selected=({'pr_number': result.admission.pr_number,
                           'generation': result.admission.generation}
                          if result.disposition == 'prepared' else None))
            if result.disposition == 'ineligible':
                continue  # ineligible/conflicted demand owns no reserved slot
            if result.disposition == 'held':
                return dict(prepared=False, disposition='held', detail=result.detail)
            self.save('reservation', dict(disposition=result.disposition, detail=result.detail))
            if result.disposition != 'prepared':
                raise RuntimeError('UNKNOWN original reservation; no next candidate')
            self.receipt('admission', asdict(result.admission), 'prepared')
            # Same original complete-history producer seals compaction before
            # dispatch. Its index lands only after immutable artifact readback.
            age_snapshot,_=mog.read_age_frontier(self.repo,self.read,repository_id=self.context['repository_id'],protected_controller_sha=self.context['protected_controller_sha'])
            checkpoint = mog.prepare_shared_checkpoint(self.repo, self.read, demand.pr_number, **self.context,age_snapshot=age_snapshot)
            self.receipt('checkpoint', asdict(checkpoint), 'checkpoint')
            return dict(prepared=True, generation=result.admission.generation, pr_number=demand.pr_number)
        return dict(prepared=False)

    def dispatch(self, prepared_artifact_id, checkpoint_artifact_id):
        self.authority()
        checkpoint_ref = self.reference('checkpoint', checkpoint_artifact_id)
        checkpoint = mog.authenticated_checkpoint_from_ref(self.repo, self.read, checkpoint_ref,
            repository_id=self.context['repository_id'], protected_controller_sha=self.context['protected_controller_sha'])
        self.index(checkpoint.pr_number, mog.CHECKPOINT_COMMENT_PREFIX, checkpoint_ref)
        ref = self.reference('prepared', prepared_artifact_id)
        result = mog.publish_prepared_shared_admission(self.repo, self.read, self.write, ref, **self.context)
        if result.disposition != 'indexed':
            raise RuntimeError('original preparation did not settle: ' + result.disposition)
        decision = {}
        result = mog.dispatch_admitted_pr_proof(self.repo, self.read, self.write, ref,
                                              decision=decision, **self.context)
        self.emit_decision('dispatch', disposition=result.disposition,
            detail=result.detail, decision=decision,
            admission=asdict(result.admission) if result.admission is not None else None)
        self.save('dispatch', dict(disposition=result.disposition, detail=result.detail))
        if result.disposition != 'bound':
            raise RuntimeError('original dispatch did not bind: ' + result.disposition)
        self.receipt('admission', asdict(result.admission), 'bound')
        return dict(bound=True, generation=result.admission.generation)

    def finalize(self, bound_artifact_id):
        self.authority()
        ref = self.reference('bound', bound_artifact_id)
        result = mog.finalize_shared_admission(self.repo, self.read, self.write, ref, **self.context)
        self.save('finalized', dict(disposition=result.disposition, detail=result.detail))
        if result.disposition != 'finalized':
            raise RuntimeError('original finalization did not settle: ' + result.disposition)
        return dict(finalized=True)

    def complete(self, run_id=None, attempt=None):
        """Reconcile current original terminal records, including coalesced wakes.

        The incumbent singleton pointer is retained THROUGH check publication.
        After a missing/ambiguous check response, the next invocation may only
        read the exact triplet; it cannot fill missing members or re-POST.
        """
        self.authority()
        inventory = mog.shared_admission_inventory(self.repo, self.read)
        if not inventory.complete or inventory.mode != 'shared':
            return dict(disposition='not_shared')
        if inventory.indexing is not None:
            return dict(disposition='held',detail='original demand indexing custody retained')
        # The complete association read retains closed PRs precisely because
        # original unknown or in-flight effects cannot expire on PR closure.
        # Do not claim a clean completion, or touch a different original,
        # while the singleton launch pointer still belongs to a closed PR.
        if inventory.launch is not None:
            owners = [issue for issue in inventory.issues
                      if issue.get('number') == inventory.launch[0]]
            if len(owners) != 1:
                return dict(disposition='unknown',
                            detail='original launch owner missing from complete inventory')
            if owners[0].get('state') == 'closed':
                return dict(disposition='held',
                            detail='closed original PR retains launch custody; no completion effect')
        root = f'{mog.GITHUB_API}/repos/{self.repo}'
        register_url = root + '/labels/' + urllib.parse.quote(mog.REFRESH_LEASE_LABEL, safe='')
        outcomes = []
        for issue in inventory.issues:
            if issue.get('state') != 'open':
                continue
            comments = mog.fetch_issue_comments(self.repo, issue['number'], self.read, strict=True)
            if comments is None:
                raise ValueError('incomplete completion inventory')
            catalog = {}
            records, _ = mog.pr_admission_history(self.repo, self.read, issue['number'], comments,
                repository_id=self.context['repository_id'],
                protected_controller_sha=self.context['protected_controller_sha'], reference_catalog=catalog)
            code, pull = mog._request('GET', root + f"/pulls/{issue['number']}", self.read)
            if code != 200 or not isinstance(pull, dict):
                raise ValueError('current completion subject unavailable')
            for a in records:
                if a.run_id is None or a.head_sha != (pull.get('head') or {}).get('sha'):
                    continue
                ref = catalog.get((a.generation, a.run_id))
                if ref is None:
                    continue  # covered settled history is never reopened
                marker = mog.admitted_subject_external_id(ref)
                checks = mog._admitted_check_inventory(mog._admitted_reads(self.repo, self.read)[0], a.head_sha)
                matching = [c for c in checks if c.get('external_id') == marker]
                if {c.get('name') for c in matching} == set(mog.ADMITTED_SUBJECT_CHECK_NAMES):
                    # Authenticate before clearing a prior UNKNOWN pointer; for
                    # already completed publication this is a read, no new POST.
                    if inventory.launch != (a.pr_number, a.generation):
                        continue
                if matching and {c.get('name') for c in matching} != set(mog.ADMITTED_SUBJECT_CHECK_NAMES):
                    return dict(disposition='unknown', detail='partial original publication; no retry')
                # Never acquire a global completion pointer for an obsolete
                # original generation. Validate every advertised later binding
                # before deciding; check text/order alone grants no credit.
                original_binding = None
                others = {c.get('external_id') for c in checks if c.get('name') in mog.ADMITTED_SUBJECT_CHECK_NAMES
                          and isinstance(c.get('external_id'), str)
                          and c['external_id'].startswith(mog.ADMITTED_SUBJECT_CHECK_PREFIX)
                          and c['external_id'] != marker}
                superseded = False
                for other in others:
                    if original_binding is None:
                        original_binding = mog._admitted_completion_binding(self.repo, self.read, ref,
                            expected_run_id=a.run_id, expected_run_attempt=a.run_attempt,
                            protected_controller_sha=self.context['protected_controller_sha'])
                    later = mog._admitted_completion_binding(self.repo, self.read,
                        mog._admitted_subject_reference(other), expected_subject_head=a.head_sha,
                        protected_controller_sha=self.context['protected_controller_sha'])
                    superseded |= mog._admitted_run_order(later) > mog._admitted_run_order(original_binding)
                if superseded:
                    continue
                observed = mog._read_admitted_run(self.repo, self.read, a, self.context['repository_id'])
                if observed.status != 'completed':
                    continue
                description = f'a2 p={a.pr_number} g={a.generation} s=completing'
                code, register = mog._request('GET', register_url, self.read)
                if code != 200 or not isinstance(register, dict):
                    raise ValueError('completion custody unavailable')
                continuing = register.get('description') == description
                if register.get('description') not in {'a2 idle', description}:
                    return dict(disposition='held', detail='original launch or completion owns pointer')
                if continuing:
                    try:
                        loaded = mog.admitted_semantic_evidence_for_head(self.repo, a.head_sha, self.read, check_runs=matching)
                        if loaded.evidence.get('run_id') != a.run_id:
                            raise ValueError('different generation')
                    except Exception:
                        return dict(disposition='unknown', detail='original completion unsettled; no retry')
                    result = dict(disposition='already_published')
                else:
                    # Preflight full original evidence BEFORE acquiring custody.
                    try:
                        mog.admitted_completion_proof(self.repo, self.read, ref,
                            expected_run_id=a.run_id, expected_run_attempt=a.run_attempt,
                            protected_controller_sha=self.context['protected_controller_sha'])
                    except Exception:
                        outcomes.append('held')  # no intent/effect: independent originals may proceed
                        continue
                    code, _ = mog._request('PATCH', register_url, self.write, {'description': description})
                    if code != 200:
                        return dict(disposition='unknown', detail='completion intent write unsettled')
                    code, register = mog._request('GET', register_url, self.read)
                    if code != 200 or register.get('description') != description:
                        return dict(disposition='unknown', detail='completion intent readback unsettled')
                    result = mog.publish_admitted_subject_checks(self.repo, self.read, self.checks, ref,
                        expected_run_id=a.run_id, expected_run_attempt=a.run_attempt,
                        protected_controller_sha=self.context['protected_controller_sha'])
                if result['disposition'] not in {'published', 'already_published'}:
                    return result  # pointer deliberately retained, no compensating clear
                code, register = mog._request('GET', register_url, self.read)
                if code != 200 or register.get('description') != description:
                    return dict(disposition='unknown', detail='completion custody changed')
                code, _ = mog._request('PATCH', register_url, self.write, {'description': 'a2 idle'})
                if code != 200:
                    return dict(disposition='unknown', detail='completion finalization unsettled')
                code, register = mog._request('GET', register_url, self.read)
                if code != 200 or register.get('description') != 'a2 idle':
                    return dict(disposition='unknown', detail='completion finalization readback unsettled')
                outcomes.append(result['disposition'])
        return dict(disposition='reconciled', count=sum(x != 'held' for x in outcomes), held=outcomes.count('held'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=['prepare', 'reserve', 'dispatch', 'finalize', 'complete'])
    args = parser.parse_args()
    context = dict(repository_id=int(os.environ['GITHUB_REPOSITORY_ID']),
                   protected_controller_sha=os.environ['GITHUB_SHA'],
                   current_run_id=os.environ['GITHUB_RUN_ID'],
                   current_run_attempt=int(os.environ['GITHUB_RUN_ATTEMPT']))
    stages = Stages(os.environ['GH_REPO'], os.environ['READ_TOKEN'], os.environ['MERGE_TOKEN'],
                    os.environ.get('CHECKS_TOKEN', ''), context, os.environ['CI_ADMISSION_STAGE_DIR'])
    if args.stage == 'prepare':
        import yaml
        workflow = yaml.safe_load((Path(__file__).resolve().parents[1] / '.github/workflows/ci.yml').read_text())
        triggers = workflow.get('on', workflow.get(True, {}))
        result = stages.prepare(native_pr_enabled='pull_request' in triggers,
            freshness=mog.ProofFreshness.build(stages.repo, stages.read))
    elif args.stage == 'reserve':
        result = stages.reserve(int(os.environ['ARTIFACT_ID']) if os.environ.get('ARTIFACT_ID') else None)
    elif args.stage == 'dispatch':
        result = stages.dispatch(int(os.environ['ARTIFACT_ID']), int(os.environ['CHECKPOINT_ARTIFACT_ID']))
    elif args.stage == 'finalize':
        result = stages.finalize(int(os.environ['ARTIFACT_ID']))
    else:
        result = stages.complete()
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
            for key, value in result.items():
                if isinstance(value, (bool, int, str)) and '\n' not in str(value):
                    output.write(f'{key}={str(value).lower() if isinstance(value, bool) else value}\n')
    print(json.dumps(result, default=str, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
