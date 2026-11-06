"""Serialize a NEW publisher commit's intended Git identity instants in UTC.

No existing commit, data/builder clock, parent, message, signing policy or global
process timezone is changed. Git itself resolves explicit ambient date syntax.
"""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import re
import subprocess
import time


def commit(root,arguments):
    if not arguments:raise ValueError('original_commit_arguments_required')
    env=dict(os.environ)
    now=str(int(time.time()))+' +0000'
    # Resolve BOTH identity instants before minting. An explicitly supplied
    # non-UTC override conserves its epoch rather than being silently replaced.
    for role in ('AUTHOR','COMMITTER'):
        env.setdefault('GIT_'+role+'_DATE',now)
        result=subprocess.run(['git','-C',str(root),'var','GIT_'+role+'_IDENT'],
            env=env,capture_output=True,timeout=30)
        match=re.fullmatch(rb'[^\n\x00]+ (-?[0-9]+) [+-][0-9]{4}\n?',result.stdout)
        if result.returncode or not match:raise ValueError('original_git_identity_date_unqualified')
        env['GIT_'+role+'_DATE']=match[1].decode()+' +0000'
    # Preserve actual hooks, configured signing and the original commit args.
    # A required signer/consent failure is not retried or weakened here.
    return subprocess.run(['git','-C',str(root),'commit',*arguments],env=env).returncode


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=Path.cwd());p.add_argument('arguments',nargs=argparse.REMAINDER);a=p.parse_args(argv)
    args=a.arguments[1:] if a.arguments[:1]==['--'] else a.arguments
    try:return commit(a.root,args)
    except (ValueError,OSError,subprocess.SubprocessError):return 76


if __name__=='__main__':raise SystemExit(main())
