"""One-off inspection of one hash-bound historical file; not an ingestion service.
Supports only flat optional BYTE_ARRAY/DOUBLE dictionary data pages v1 and Snappy.
Specification: Apache Parquet parquet.thrift and data-page encodings.
"""
from __future__ import annotations
import ctypes, hashlib, struct
from pathlib import Path
from thrift.protocol.TCompactProtocol import TCompactProtocol
from thrift.transport.TTransport import TMemoryBuffer
from thrift.Thrift import TType

EXPECTED='01a732f8e4d5db94011957797b9df9ba1c865aa3'

def hybrid(data:bytes,width:int,n:int)->list[int]:
 if not 0 <= width <=32 or n<0: raise ValueError('invalid dimensions')
 out=[]; pos=0
 while len(out)<n:
  h=0; shift=0
  while True:
   if pos>=len(data) or shift>35:raise ValueError('truncated/invalid header')
   b=data[pos];pos+=1;h|=(b&127)<<shift;shift+=7
   if not b&128:break
  if h<=1:raise ValueError('empty run')
  if h&1:
   count=(h>>1)*8;size=(count*width+7)//8
   if pos+size>len(data):raise ValueError('truncated packed values')
   packed=int.from_bytes(data[pos:pos+size],'little');pos+=size
   out.extend((packed>>(i*width))&((1<<width)-1) for i in range(count))
  else:
   count=h>>1;size=(width+7)//8
   if pos+size>len(data):raise ValueError('truncated repeated value')
   v=int.from_bytes(data[pos:pos+size],'little');pos+=size;out.extend([v]*count)
  if len(out)>max(n+7,2_000_000):raise ValueError('unbounded run')
 return out[:n]

def plain(data:bytes,typ:int,n:int)->list:
 if typ==5:
  if len(data)<n*8:raise ValueError('truncated double')
  return list(struct.unpack('<'+'d'*n,data[:8*n]))
 if typ!=6:raise ValueError('unsupported type')
 out=[];pos=0
 for _ in range(n):
  if pos+4>len(data):raise ValueError('truncated length')
  size=struct.unpack_from('<I',data,pos)[0];pos+=4
  if pos+size>len(data):raise ValueError('truncated string')
  out.append(data[pos:pos+size].decode('utf-8'));pos+=size
 return out

def readvalue(p,t):
 scalar={TType.BOOL:p.readBool,TType.BYTE:p.readByte,TType.I16:p.readI16,TType.I32:p.readI32,TType.I64:p.readI64,TType.DOUBLE:p.readDouble,TType.STRING:p.readBinary}
 if t in scalar:return scalar[t]()
 if t==TType.STRUCT:
  out={};p.readStructBegin()
  while True:
   _,ft,fid=p.readFieldBegin()
   if ft==TType.STOP:break
   out[fid]=readvalue(p,ft);p.readFieldEnd()
  p.readStructEnd();return out
 if t in (TType.LIST,TType.SET):
  ft,n=p.readListBegin();out=[readvalue(p,ft) for _ in range(n)];p.readListEnd();return out
 if t==TType.MAP:
  kt,vt,n=p.readMapBegin();out={readvalue(p,kt):readvalue(p,vt) for _ in range(n)};p.readMapEnd();return out
 raise ValueError('unsupported thrift field')

def thrift_at(b:bytes,offset:int):
 t=TMemoryBuffer(b[offset:]);p=TCompactProtocol(t)
 value=readvalue(p,TType.STRUCT)
 return value,t.cstringio_buf.tell()

def uncompress(b:bytes,size:int)->bytes:
 if size<0 or size>4_000_000:raise ValueError('invalid output size')
 lib=ctypes.CDLL('libsnappy.so.1')
 lib.snappy_uncompress.argtypes=[ctypes.c_char_p,ctypes.c_size_t,ctypes.c_void_p,ctypes.POINTER(ctypes.c_size_t)]
 lib.snappy_uncompress.restype=ctypes.c_int
 output=ctypes.create_string_buffer(size);n=ctypes.c_size_t(size)
 if lib.snappy_uncompress(b,len(b),output,ctypes.byref(n))!=0 or n.value!=size:raise ValueError('bad snappy page')
 return output.raw

def read_snapshot(path:Path)->tuple[list[dict],dict]:
 b=path.read_bytes();sha=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
 if sha!=EXPECTED:raise ValueError('only the explicitly recovered snapshot is admitted')
 if b[:4]!=b'PAR1' or b[-4:]!=b'PAR1':raise ValueError('not parquet')
 footer=struct.unpack_from('<I',b,len(b)-8)[0];m,_=thrift_at(b,len(b)-8-footer)
 schema=m[2];n=m[3]
 if len(m[4])!=1:raise ValueError('one row group required')
 columns={};checks=[]
 for chunk in m[4][0][1]:
  cm=chunk[3];name=cm[3][0].decode();typ=cm[1]
  leaf=next(s for s in schema if s.get(4)==name.encode())
  if len(cm[3])!=1 or leaf.get(3)!=1 or typ not in(5,6) or cm[4]!=1:raise ValueError('unsupported column layout')
  pos=cm.get(11,cm[9]);end=pos+cm[7];dictionary=None;out=[]
  while pos<end:
   h,hs=thrift_at(b,pos);pos+=hs
   raw=b[pos:pos+h[3]];pos+=h[3];data=uncompress(raw,h[2])
   if h[1]==2:
    dh=h[7]
    if dh[2]!=0:raise ValueError('unsupported dictionary encoding')
    dictionary=plain(data,typ,dh[1]);continue
   if h[1]!=0:raise ValueError('unsupported page version')
   dh=h[5];count=dh[1]
   if dh[3]!=3:raise ValueError('unsupported definition levels')
   size=struct.unpack_from('<I',data,0)[0]
   levels=hybrid(data[4:4+size],1,count);payload=data[4+size:];valid=sum(levels)
   if any(l not in(0,1) for l in levels):raise ValueError('invalid optional level')
   if dh[2] in(2,8):
    if dictionary is None or not payload:raise ValueError('missing dictionary')
    ids=hybrid(payload[1:],payload[0],valid)
    vals=[dictionary[i] for i in ids]
   elif dh[2]==0:vals=plain(payload,typ,valid)
   else:raise ValueError('unsupported value encoding')
   it=iter(vals);out.extend(next(it) if l else None for l in levels)
  if pos!=end or len(out)!=n or cm[5]!=n:raise ValueError('count/boundary mismatch')
  stats=cm.get(12,{})
  if 3 in stats and stats[3]!=out.count(None):raise ValueError('null count mismatch')
  nonnull=[v for v in out if v is not None]
  for field,fun in ((5,max),(6,min)):
   if field in stats and nonnull:
    rawv=stats[field];expected=struct.unpack('<d',rawv)[0] if typ==5 else rawv.decode()
    if fun(nonnull)!=expected:raise ValueError('statistics mismatch')
  checks.append({'name':name,'count':len(out),'nulls':out.count(None),'page_boundary_and_stats_match':True})
  columns[name]=out
 rows=[dict(zip(columns,vs)) for vs in zip(*columns.values())]
 if len(set(r['ticker'] for r in rows))!=n:raise ValueError('nonunique index')
 return rows,{'rows':n,'columns':list(columns),'column_checks':checks,'file_blob':sha,'sha256':hashlib.sha256(b).hexdigest()}
