"""Explicit same-host private delivery client; no import IO or default activation."""
from __future__ import annotations
import json, os, selectors, subprocess, time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

FIELDS=('id','user_id','alert_id','fire_event_id','channel','status','payload','attempts','deliver_after')


def origin(value):
    if not isinstance(value,str):return None
    p=urlsplit(value)
    if p.scheme!='https' or not p.netloc or p.username or p.password or p.path not in ('','/') or p.query or p.fragment:return None
    return value.rstrip('/')


def pinned(row):
    value={k:row[k] for k in FIELDS}
    return json.dumps(value,allow_nan=False,sort_keys=True,separators=(',',':'))


@dataclass(frozen=True)
class FrozenEmailAdmission:
    source_origin: str
    row_json: str
    def matches(self,row):
        try:return pinned(row)==self.row_json
        except Exception:return False


def invoke(command,request,env):
    body=json.dumps(request,allow_nan=False,separators=(',',':')).encode()
    if len(body)>262144:return None
    p=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,env=env)
    poll=selectors.DefaultSelector();out=bytearray();sent=0;deadline=time.monotonic()+20
    try:
        os.set_blocking(p.stdin.fileno(),False);os.set_blocking(p.stdout.fileno(),False)
        poll.register(p.stdin,selectors.EVENT_WRITE);poll.register(p.stdout,selectors.EVENT_READ)
        while poll.get_map():
            if time.monotonic()>=deadline:return None
            for key,_ in poll.select(min(.2,max(0,deadline-time.monotonic()))):
                if key.fileobj is p.stdin:
                    sent+=os.write(p.stdin.fileno(),body[sent:sent+65536])
                    if sent==len(body):poll.unregister(p.stdin);p.stdin.close()
                else:
                    chunk=os.read(p.stdout.fileno(),65536)
                    if not chunk:poll.unregister(p.stdout)
                    else:
                        out.extend(chunk)
                        if len(out)>262144:return None
        p.wait(timeout=max(.001,deadline-time.monotonic()))
        if p.returncode!=0:return None
        return json.loads(out.decode('utf-8','strict'),parse_constant=lambda _:(_ for _ in ()).throw(ValueError()))
    except Exception:return None
    finally:
        poll.close()
        if p.poll() is None:p.kill()
        p.wait()
        if not p.stdin.closed:p.stdin.close()
        p.stdout.close()


class FrozenEmailDelivery:
    def __init__(self, *, python, script, env_file, source_origin, env=None):
        exe,script,config=Path(python),Path(script),Path(env_file)
        if (not exe.is_absolute() or not exe.is_file() or not os.access(exe,os.X_OK)
                or not script.is_absolute() or not script.is_file() or script.name!='options_frozen_delivery_cli.py'
                or not config.is_absolute() or not config.is_file() or config.stat().st_size>65536):
            raise ValueError('unqualified frozen-delivery host paths')
        declared={}
        for line in config.read_text().splitlines():
            if '=' in line and not line.strip().startswith('#'):
                k,v=line.split('=',1);declared[k.strip()]=v.strip().strip('"').strip("'")
        if origin(source_origin) is None or origin(declared.get('SUPABASE_URL'))!=origin(source_origin):
            raise ValueError('mismatched private delivery database')
        self.origin=origin(source_origin);self.command=(str(exe),str(script))
        self.env={**(dict(os.environ) if env is None else dict(env)),
            'OPTIONS_FROZEN_DELIVERY_ENABLED':'1','OPTIONS_FROZEN_DELIVERY_ENV_FILE':str(config)}

    def authorize(self,row,evaluation_at):
        try:
            raw=pinned(row);snap=json.loads(raw)
            reply=invoke(self.command,dict(mode='email',row=snap,evaluationAt=evaluation_at,sourceOrigin=self.origin),self.env)
            if (not isinstance(reply,dict) or set(reply)!={'kind','mode','sourceOrigin','evaluationAt','row'}
                    or reply['kind']!='admitted_delivery' or reply['mode']!='email'
                    or reply['sourceOrigin']!=self.origin or reply['evaluationAt']!=evaluation_at
                    or pinned(reply['row'])!=raw):return None
            return FrozenEmailAdmission(self.origin,raw)
        except Exception:return None


def from_environment(deployment):
    config=dict(deployment);enabled=config.get('OPTIONS_FROZEN_DELIVERY_ENABLED')
    if enabled in (None,'','0'):return None
    if enabled!='1':raise ValueError('invalid frozen-delivery opt-in')
    return FrozenEmailDelivery(python=config['OPTIONS_FROZEN_DELIVERY_PYTHON'],
        script=config['OPTIONS_FROZEN_DELIVERY_SCRIPT'],env_file=config['OPTIONS_FROZEN_DELIVERY_ENV_FILE'],
        source_origin=config.get('SUPABASE_URL'),env=config)
