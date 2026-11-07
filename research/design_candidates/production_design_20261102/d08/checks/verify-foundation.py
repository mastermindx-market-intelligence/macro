"""Calculate candidate shell boundaries; never represents browser or joint approval."""
import json

def geometry(width, compact=False, owner='F01'):
    if not isinstance(width,(int,float)) or width <= 0: raise ValueError('positive CSS width required')
    if width <= 860: rail=0
    elif compact: rail=72
    elif width >= 1200: rail=224
    elif owner=='F02' or 861 <= width <= 1199: rail=196
    else: return {'state':'UNDERSPECIFIED_FRACTIONAL_INTERVAL','owner':owner,'viewport':width}
    gutter=(16 if width < 768 else 20 if width < 1200 else 24) if owner=='F01' else (16 if width <= 600 else 20 if width < 1200 else 24)
    content=width-rail-2*gutter
    return {'state':'CALCULATED_NOT_RENDERED','owner':owner,'viewport':width,'compact':compact,'rail':rail,'gutter':gutter,'usable':content,'dock':content>=984,'primary_if_docked':content-344}

checks=[]
def check(name, value):
    assert value,name
    checks.append({'name':name,'status':'PASS'})
for w,c in [(320,288),(390,358),(768,728),(1024,788),(1280,1008),(1440,1168),(1600,1328)]:
    check(f'agreed usable width {w}',geometry(w)['usable']==geometry(w,owner='F02')['usable']==c)
check('expanded 1255 refuses dock',not geometry(1255)['dock'])
check('expanded 1256 allows 640px primary',geometry(1256)['primary_if_docked']==640)
check('compact 1095 refuses dock',not geometry(1095,True)['dock'])
check('compact 1096 allows 640px primary',geometry(1096,True)['primary_if_docked']==640)
for w in [600.5,601,640,767,767.5]:
    check(f'known gutter disagreement at {w}',geometry(w)['usable']-geometry(w,owner='F02')['usable']==8)
check('gutter agreement returns at 768',geometry(768)['gutter']==geometry(768,owner='F02')['gutter'])
for w in [860.5,1199.5]:
    check(f'F01 literal interval unresolved at {w}',geometry(w)['state']=='UNDERSPECIFIED_FRACTIONAL_INTERVAL')
    check(f'F02 exhaustive proposed interval at {w}',geometry(w,owner='F02')['rail']==196)
check('overlay proposals differ by 40px',440-400==40)
widths=[320,390,600,600.5,601,640,767,767.5,768,860,860.5,861,1024,1095,1096,1199,1199.5,1200,1255,1256,1280,1440,1600]
print(json.dumps({'schema':'d08.foundation.reconciliation.v1','evidence_class':'CALCULATION_NOT_BROWSER','joint_release':'NOT_QUALIFIED','F01_sha':'b2d00ddc7e2dfbffdc3c5855e1a4dffe8c4226a5','F02_sha':'f7c25c4b9870cff260c2a4b998be18d6c04d36d0','passed':len(checks),'checks':checks,'cases':[{'viewport':w,'F01':geometry(w),'F02':geometry(w,owner='F02')} for w in widths]},indent=2))
