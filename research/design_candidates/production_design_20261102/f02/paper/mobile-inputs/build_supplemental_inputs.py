#!/usr/bin/env python3
"""Prepare only the F02 coverage supplement; no Paper or browser effects."""
import copy
import hashlib
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import build_mobile_inputs as base
import compare_clones as clones

text,frame,row,button,board,add=base.text,base.frame,base.row,base.button,base.board,base.add
P=base.PALETTES
RECORD_ID='f02.fixture.v2/macro/sector/communication_services/share_above_50d/2026-10-30'
SYSTEM=(HERE.parents[1]/'SYSTEM_CONTRACT.md').read_text()

def band(b,label,lang='en'):
    t=b['theme'];add(b,'artifact','board',row('F02 supplemental provenance',text(label,11,'secondary',500,t,16,lang=lang),'width: '+str(b['width'])+'px;height: 30px;padding: 0 16px;background-color: '+P[t]['raised']+';'))

def close_control(theme='light',zh=False):
    p=P[theme]
    return row('Close evidence — initial focus',text('关闭' if zh else 'Close',12,'ink',500,theme,18,lang='zh' if zh else 'en'),
      'width: 44px;height: 44px;justify-content: center;border: 1px solid '+p['control-line']+';border-radius: 6px;outline: 2px solid '+p['focus']+';outline-offset: 2px;background-color: '+p['panel']+';')

def fact(label,value,width,theme='light',lang='en'):
    return frame(label,text(label,12,'muted',500,theme,18,lang=lang)+text(value,13,'ink',400,theme,20,'width: '+str(width)+'px;overflow-wrap: anywhere;',lang),
      'width: '+str(width)+'px;gap: 4px;')

def chinese_journey():
    t='light';p=P[t]
    b=board('macro-zh-evidence-return-390','F02 · 中文行业证据与返回 · 390 · Candidate 2','p-5-0',390,1460,t,'zh')
    band(b,'F02 / 390 CSS px / 中文证据与返回 / 设计候选','zh')
    add(b,'dialog-header','board',row('行业证据对话框标题',text('行业证据',18,'ink',600,t,26,'flex-grow: 1;',lang='zh')+close_control(t,True),
      'width: 390px;height: 64px;padding: 0 16px;gap: 16px;background-color: '+p['panel']+';border-bottom: 1px solid '+p['line']+';'))
    add(b,'body','board',frame('390px证据正文','', 'width: 390px;padding: 20px;gap: 16px;background-color: '+p['bg']+';'))
    add(b,'entity','body',frame('准确的行业身份',text('示例来源 · 与行业对比中的选中行一致',12,'accent',600,t,18,lang='zh')+text('通信服务',26,'ink',600,t,34,lang='zh')+text('Communication services · 示例行业子集',13,'secondary',400,t,20,lang='zh'),'width: 350px;gap: 6px;'))
    values=[('高于50日均线','66.7%','ink'),('较上一已结算交易日','+1.13 pp','up'),('已覆盖 / 符合条件','21 / 21','ink')]
    add(b,'values','body',frame('完整选中行的数值','', 'width: 350px;'))
    for i,(label,value,col) in enumerate(values):
        add(b,'value-'+str(i),'values',row(label,text(label,13,'secondary',400,t,20,'width: 220px;',lang='zh')+text(value,20 if i==0 else 17,col,500,t,28,'width: 130px;text-align: right;font-variant-numeric: tabular-nums;'),
          'width: 350px;height: 44px;border-bottom: 1px solid '+p['line']+';'))
    add(b,'baseline','body',text('上期65.57% → 本期66.70%；差值为+1.13个百分点，不是相对增长1.13%。',13,'secondary',400,t,21,lang='zh'))
    add(b,'source-identity','body',fact('来源标识',RECORD_ID,350,t,'zh'))
    clock_rows=[('观测','2026年10月30日 · 已结算20:00 UTC'),('发布','2026年10月30日 · 20:02 UTC'),('获取','2026年10月30日 · 20:03 UTC')]
    clocks=''.join(row(label,text(label,12,'muted',500,t,20,'width: 52px;',lang='zh')+text(value,13,'ink',400,t,20,'width: 298px;',lang='zh'),'width: 350px;') for label,value in clock_rows)
    add(b,'source-clocks','body',frame('三个时钟分别记录',clocks,'width: 350px;gap: 8px;'))
    add(b,'units','body',fact('单位与范围','比例：百分比；变化：百分点（pp）。当前行表示通信服务行业，不是市场总体。',350,t,'zh'))
    add(b,'coverage-limit','body',frame('不能混用的覆盖范围',text('覆盖范围说明',13,'ink',600,t,20,lang='zh')+text('本行21/21与八期总体历史的7/8描述不同群体，不可合并。示例数值不代表实时生产者响应。',13,'secondary',400,t,21,lang='zh'),
      'width: 350px;padding: 16px;background-color: '+p['raised']+';gap: 6px;'))
    add(b,'return-action','body',button('返回“通信服务”行',t,350,44,lang='zh'))
    contract='单一命名模态：初始焦点在“关闭”，Tab / Shift+Tab留在对话框内，背景不可操作；Esc或关闭后返回同一来源按钮，并保留排序、筛选与横向滚动。若该行已不在视图中，焦点返回“行业对比”标题并宣布原因。'
    add(b,'modal-contract','body',frame('相邻交互说明',text('构建说明 · 不是已执行的交互测试',12,'ink',600,t,18,lang='zh')+text(contract,12,'secondary',400,t,19,lang='zh')+text('打开、关闭或切换语言均不保存，也不创建新的URL。保留现有路由、实体键和历史行为。',12,'secondary',400,t,19,lang='zh'),
      'width: 350px;padding-top: 16px;border-top: 1px solid '+p['line']+';gap: 8px;'))
    add(b,'return-state','board',frame('关闭后的返回状态示例',text('关闭后：回到同一“通信服务”来源按钮',14,'ink',600,t,22,lang='zh')+text('选中填色与键盘焦点独立；仍是原来的650px行。',12,'secondary',400,t,18,lang='zh'),
      'width: 390px;padding: 20px 16px 12px;background-color: '+p['raised']+';gap: 6px;'))
    add(b,'return-row-viewport','board',frame('返回时的358px表格视口','', 'width: 390px;padding: 0 16px;background-color: '+p['raised']+';'))
    add(b,'return-row-clip','return-row-viewport',frame('原表格的局部滚动区域','', 'width: 358px;height: 56px;overflow: hidden;'))
    original=base.mobile_macro('light','zh')
    selected=next(s['html'] for s in original['steps'] if s['key']=='sector-3')
    add(b,'returned-selected-row','return-row-clip',selected,'Exact input match to macro-light-zh-390 / sector-3. Parent may clone the observed source row and bind its actual mapped IDs.')
    b['steps'][-1]['checkpoint_after']=True
    add(b,'return-note','board',frame('返回状态验证边界',text('此返回状态是可编辑设计示例；真实焦点恢复、滚动保留、触控与400%缩放仍需浏览器验证。',12,'secondary',400,t,19,lang='zh'),
      'width: 390px;padding: 16px;background-color: '+p['raised']+';'))
    b['expected_geometry']={'viewport':390,'dialog_width':390,'dialog_body':350,'comparison_content':358,'row_intrinsic':650,'control':44,'record_id':RECORD_ID,'modal':'full available width at <=600px in existing specimen','return_identity':'same Communication services record, not row position'}
    return b

def width_overlay(width):
    assert width in [768,1024]
    t='dark';p=P[t];rail=0 if width==768 else 196;pad=20;usable=width-rail-2*pad;header=56 if width==768 else 64
    b=board('width-'+str(width)+'-overlay','F02 · '+str(width)+'px width evaluation · Evidence overlay','p-5-0',width,1130,t)
    band(b,'F02 / '+str(width)+' CSS px / PROVISIONAL SHELL WIDTH EVALUATION')
    add(b,'scene','board',frame('Exact '+str(width)+'px application viewport','', 'position: relative;width: '+str(width)+'px;height: 900px;overflow: hidden;background-color: '+p['bg']+';'))
    add(b,'header','scene',row('Observed shell header',text('MASTERMIND',13,'ink',600,t,20,'flex-grow: 1;letter-spacing: 0.06em;')+text(str(width)+'px · fixture view',12,'secondary',400,t,18),
      'width: '+str(width)+'px;height: '+str(header)+'px;padding: 0 20px;background-color: '+p['rail']+';border-bottom: 1px solid '+p['line']+';'))
    add(b,'workspace','scene',row('Rail and available primary content','', 'width: '+str(width)+'px;align-items: stretch;'))
    if rail:
        nav=row('Analysis context',text('Analysis',14,'ink',600,t,22),'width: 164px;height: 44px;padding: 0 12px;border-radius: 6px;background-color: '+p['selected']+';')
        add(b,'rail','workspace',frame('Observed 196px navigation envelope',text('F01 NAVIGATION',11,'muted',600,t,18,'padding: 0 12px 12px;')+nav+text('196px observed width. This is a width study; the full navigation remains F01-owned.',12,'muted',400,t,19,'padding: 20px 12px 0;'),
          'width: 196px;min-height: 836px;padding: 24px 16px;background-color: '+p['rail']+';border-right: 1px solid '+p['line']+';gap: 4px;'))
    add(b,'main','workspace',frame(str(usable)+'px primary content before overlay','', 'width: '+str(width-rail)+'px;padding: 20px;gap: 16px;'))
    add(b,'heading','main',frame('Comparison question and period',text('Market breadth',26,'ink',600,t,34)+text('Illustrative sector subset · 30 Oct 2026, 20:00 UTC',13,'secondary',400,t,20),
      'width: '+str(usable)+'px;gap: 6px;'))
    add(b,'table-label','main',row('Dense comparison context',text('Sector comparison',16,'ink',600,t,24,'flex-grow: 1;')+text('10 rows · 9 available',12,'secondary',400,t,18),
      'width: '+str(usable)+'px;height: 32px;'))
    widths=[usable-452,104,92,128,104]
    labels=['Sector','Above 50D','Δ pp','Covered / eligible','Source']
    headers=''.join(text(label,12,'secondary',500,t,18,'width: '+str(w)+'px;flex-shrink: 0;'+('text-align: right;padding-right: 12px;' if i in [1,2,3] else '')) for i,(label,w) in enumerate(zip(labels,widths)))
    add(b,'table','main',frame('All fields retained in the width evaluation',row('Column headers',headers,
      'width: '+str(usable)+'px;height: 40px;padding: 0 12px;background-color: '+p['raised']+';'),'width: '+str(usable)+'px;'))
    for i,r in enumerate(base.MACRO):
        vals=[r[0],'—' if r[2] is None else f'{r[2]:.1f}%','—' if r[3] is None else f'{r[3]:+.2f}' if r[3] else '0.00',r[4]]
        inner=''
        for j,(v,w) in enumerate(zip(vals,widths)):
            col='ink' if j in [0,1] else ('muted' if r[3] is None else 'up' if r[3]>0 else 'down' if r[3]<0 else 'ink') if j==2 else 'secondary'
            inner+=text(v,13,col,600 if i==3 and j==0 else 400,t,20,'width: '+str(w)+'px;flex-shrink: 0;'+('text-align: right;padding-right: 12px;font-variant-numeric: tabular-nums;' if j else 'padding-right: 8px;'))
        inner+=row('Row-specific source action',button('Source',t,88,32,focus=i==3),'width: 104px;')
        add(b,'sector-'+str(i),'table',row('Sector '+r[0],inner,
          'width: '+str(usable)+'px;height: 40px;padding: 0 12px;background-color: '+p['selected' if i==3 else 'panel']+';border-bottom: 1px solid '+p['line']+';'))
        if i in [2,5,9]:b['steps'][-1]['checkpoint_after']=True
        if i==9:b['steps'][-1]['capture_state']='CLOSED_BEFORE_OVERLAY: capture native table/main now; every field and all ten rows are visible.'
    add(b,'underlay-note','main',frame('Closed-width geometry contract',text(str(width)+' − '+str(rail)+' rail − 40 padding = '+str(usable)+'px primary.',14,'ink',600,t,22)+text('A 320px dock plus 24px gap would leave '+str(usable-344)+'px, below the 640px primary minimum. Open a modal; do not shrink this comparison or force compact navigation.',13,'secondary',400,t,20),
      'width: '+str(usable)+'px;gap: 6px;'))
    add(b,'backdrop','scene',frame('Modal background — inert in implementation','', 'position: absolute;left: 0px;top: 0px;width: '+str(width)+'px;height: 900px;background-color: #0008;'))
    add(b,'overlay','scene',frame('440px right-side evidence overlay','', 'position: absolute;right: 0px;top: 0px;width: 440px;height: 900px;background-color: '+p['panel']+';border-left: 1px solid '+p['line']+';'))
    add(b,'overlay-header','overlay',row('Evidence dialog header',text('Evidence',18,'ink',600,t,26,'flex-grow: 1;')+close_control(t), 'width: 439px;height: 64px;padding: 0 16px;gap: 16px;border-bottom: 1px solid '+p['line']+';'))
    add(b,'overlay-body','overlay',frame('Evidence dialog body','', 'width: 439px;padding: 20px;gap: 14px;'))
    add(b,'overlay-entity','overlay-body',frame('Selected sector evidence',text('ILLUSTRATIVE SOURCE',11,'accent',600,t,18)+text('Communication services',24,'ink',600,t,30)+text('Share above the 50-day moving average',13,'secondary',400,t,20), 'width: 399px;gap: 6px;'))
    values=row('Selected row values',frame('Above 50D',text('Above 50D',12,'secondary',400,t,18)+text('66.7%',28,'ink',500,t,36),'width: 133px;gap: 4px;')+frame('Change in percentage points',text('Δ vs prior session',12,'secondary',400,t,18)+text('+1.13 pp',18,'up',500,t,28),'width: 133px;gap: 4px;')+frame('Covered eligible count',text('Covered / eligible',12,'secondary',400,t,18)+text('21 / 21',18,'ink',500,t,28),'width: 133px;gap: 4px;'),'width: 399px;align-items: flex-start;')
    add(b,'overlay-values','overlay-body',values)
    add(b,'overlay-source','overlay-body',fact('Source identity',RECORD_ID,399,t))
    c=''.join(row(label,text(label,12,'muted',500,t,20,'width: 92px;')+text(value,13,'ink',400,t,20,'width: 307px;'),'width: 399px;') for label,value in [('Observed','30 Oct 2026 · settled 20:00 UTC'),('Published','30 Oct 2026 · 20:02 UTC'),('Retrieved','30 Oct 2026 · 20:03 UTC')])
    add(b,'overlay-clocks','overlay-body',frame('Separate source clocks',c,'width: 399px;gap: 8px;'))
    add(b,'overlay-limit','overlay-body',frame('Units and scope',text('Units: percent; change in percentage points.',13,'ink',500,t,20)+text('Row coverage 21/21 differs from universe-history coverage 7/8. The fixture is not a market total or a live source response.',13,'secondary',400,t,20),'width: 399px;gap: 8px;'))
    add(b,'overlay-return','overlay-body',button('Return to Communication services',t,399,44))
    add(b,'overlay-contract','overlay-body',frame('Modal behavior contract',text('Modal · not a dock',13,'ink',600,t,20)+text('Background inert; Tab stays inside; Escape/Close returns to the same row source trigger and table scroll. If filtering removes that row, focus the named comparison heading and explain why.',12,'secondary',400,t,19)+text('Opening or closing is read-only. Existing route/query/hash and source identity remain owned by the current consumer.',12,'secondary',400,t,19),
      'width: 399px;padding-top: 14px;border-top: 1px solid '+p['line']+';gap: 8px;'))
    b['steps'][-1]['checkpoint_after']=True;b['steps'][-1]['capture_state']='OPEN_OVERLAY: capture exact viewport; primary geometry remains unchanged behind modal.'
    add(b,'evaluation-note','board',frame('Width evaluation and proof limits',text(str(width)+'px evaluation: '+str(usable)+'px underlying primary; 440px overlay.',16,'ink',600,t,24)+text('The complete ten-row/five-column comparison remains native behind the overlay. Capture it before adding the backdrop and again after closing/hiding it through the actual implementation. The darkened background is intentional modal occlusion, not dropped data.',13,'secondary',400,t,21)+text('F01 shell release is provisional. This specifies geometry and interaction; it does not prove browser input, zoom, focus trapping or server behavior.',12,'muted',400,t,19),
      'width: '+str(width)+'px;padding: 20px;gap: 8px;'))
    b['expected_geometry']={'viewport':width,'header':header,'rail':rail,'side_padding':20,'primary_without_inspector':usable,'hypothetical_docked_primary':usable-344,'primary_minimum':640,'evidence':'440px overlay from existing specimen CSS; no primary reflow','overlay_left':width-440,'table_fields':['Sector','Above 50D','Change in percentage points','Covered/eligible','Source action'],'rows':10,'source_column_present':True}
    return b

def wide_dock():
    b=copy.deepcopy(base.dock_stress());b['key']='width-1600-docked';b['name']='F02 · 1600px width evaluation · 984px comparison + 320px dock';b['width']=1600
    for s in b['steps']:
        key=s['key'];h=s['html']
        if key=='artifact':h=h.replace('1280 CSS px','1600 CSS px')
        if key in ['header','workspace']:h=h.replace('width: 1280px;','width: 1600px;')
        if key=='main':h=h.replace('width: 1056px;','width: 1376px;')
        if key in ['title','split','width-contract']:h=h.replace('width: 1008px;','width: 1328px;')
        if key in ['primary','comparison-heading','table','history-heading','chart-footer'] or key.startswith('sector-'):
            h=h.replace('width: 664px;','width: 984px;')
        if key=='table' or key.startswith('sector-'):
            sizes={228:428,104:144,92:116,128:184}
            h=re.sub(r'width: (228|104|92|128)px;',lambda m:'width: '+str(sizes[int(m[1])])+'px;',h)
        if key=='chart':h=base.small_chart('dark','en',984)
        if key=='width-contract':
            h=frame('Provisional width acceptance',text('1600 − 224 rail − 48 padding = 1328px usable',15,'ink',600,line=22)+text('1328 − 320 dock − 24 gap = 984px primary; exceeds the candidate 640px minimum.',13,'secondary',line=21)+text('Same data, five table fields and exact source access. F01 joint release and real browser/keyboard/400% proof remain open.',12,'muted',line=19),'width: 1328px;padding-top: 20px;border-top: 1px solid '+P['dark']['line']+';gap: 6px;')
        s['html']=h
    b['expected_geometry']={'viewport_width':1600,'rail':224,'header':64,'main_padding':24,'main_usable':1328,'dock':320,'gap':24,'primary':984,'primary_minimum':640,'shell_release':'PROVISIONAL; F01 joint freeze open','source_column_present':True,'rows':10}
    return b

def state_row(key,state,head,copy_,action,condition):
    cells=frame(state,text(state,14,'ink',600,line=20)+text(condition,11,'secondary',400,line=16),'width: 184px;padding: 12px;gap: 6px;border-bottom: 1px solid '+P['dark']['line']+';')
    for t in ['dark','light']:
        contents=frame(t.title()+' copy',text(head,15,'ink',600,t,22)+text(copy_,13,'secondary',400,t,20),'width: 416px;gap: 4px;')+button(action,t,144,36)
        cells+=row(t.title()+' outcome cell',contents,'width: 600px;min-height: 112px;padding: 12px;gap: 16px;background-color: '+P[t]['panel']+';border-bottom: 1px solid '+P[t]['line']+';')
    return {'key':key,'parent':'matrix','html':row('State comparison · '+state,cells,'width: 1384px;min-height: 112px;align-items: stretch;')}

def append_groups():
    # Existing controls artboard has48px padding, leaving1344px usable.
    controls=[]
    controls.append({'key':'supplement-hover-heading','parent':'board','html':frame('Hover is not selection or focus',text('Pointer hover is a separate state.',21,'ink',600,line=30)+text('Hover alone does not activate a tab, persist selection, move keyboard focus, change access or save.',13,'secondary',line=21),'width: 1344px;gap: 8px;')})
    examples=''
    for label,fill,selected,focus in [('Default','panel',False,False),('Hover','hover',False,False),('Selected','selected',True,False),('Keyboard focus','panel',False,True)]:
        p=P['dark'];bg='var(--noir-hover)' if fill=='hover' else p[fill]
        focus_style='outline: 2px solid '+p['focus']+';outline-offset: 3px;' if focus else ''
        control=row('Table tab · '+label,text('Table',13,'ink',600 if selected else 400,line=20),'width: 180px;height: 44px;justify-content: center;background-color: '+bg+';border: 1px solid '+p['control-line']+';border-radius: 6px;'+focus_style)
        note={'Default':'Not selected; not focused.','Hover':'Pointer present; no activation.','Selected':'Current panel; quiet neutral fill.','Keyboard focus':'Unselected tab; Enter / Space activates.'}[label]
        examples+=frame(label,text(label,14,'ink',600,line=20)+control+text(note,12,'secondary',line=18),'width: 318px;gap: 12px;')
    controls.append({'key':'supplement-hover-row','parent':'board','html':row('Default, hover, selected and focus variants',examples,'width: 1344px;gap: 24px;align-items: flex-start;'),'checkpoint_after':True})
    states=[state_row('supplement-source-unavailable','Source unavailable','This source is unavailable.','Other available evidence remains visible with its own source context.','View coverage','Availability · source failure; do not infer an access denial.'),
      state_row('supplement-access-service-unavailable','Access service unavailable','We couldn’t check your access.','Public evidence remains available. The access service has not confirmed permission for this source.','Retry access check','Access · provider unavailable; not plan denied or session expired.')]
    states[-1]['checkpoint_after']=True
    contract=frame('Unavailable source and unavailable access provider',text('Different failures, different owners.',17,'ink',600,line=24)+text('Source unavailable: preserve source-specific coverage and any valid dated snapshot; “View coverage” opens the existing coverage receipt. A source retry is offered only when the producer owner supplies that read callback.',13,'secondary',line=21)+text('Access provider unavailable: the current entitlement owner may retry the existing access check. Do not label the user denied, expired or in need of a different plan. The server withholds protected payload until permission is established; keep public evidence available. No sign-in, plan, save or duplicate request is silently created.',13,'secondary',line=21)+text('中文文案：此来源不可用，仍显示其他可用证据。／暂时无法核实访问权限，公开证据仍可查看；重试现有权限检查。',13,'secondary',line=21,lang='zh'),'width: 1440px;padding: 20px 28px;gap: 8px;')
    return [
      {'target_board_key':'controls','target_packet':'foundation-inputs/boards.json','steps':controls,'resize_after':'Verify current height; use measured fit-content when needed.'},
      {'target_board_key':'states-matrix','target_packet':'mobile-inputs/mobile-state-boards.json','steps':states+[{'key':'supplement-unavailable-contract','parent':'board','html':contract}],'resize_after':'Verify current height after two added rows and contract; do not overwrite existing state rows.'}]

def main():
    original_path=HERE/'mobile-state-boards.json';before=hashlib.sha256(original_path.read_bytes()).hexdigest()
    boards=[chinese_journey(),width_overlay(768),width_overlay(1024),wide_dock()]
    hints=[{'kind':'exact_native_subtree_candidate','source_board_key':'macro-light-zh-390','source_step_key':'sector-3','target_board_key':'macro-zh-evidence-return-390','target_step_key':'returned-selected-row','source_and_target_input_equal':True,'binding':'Use observed source ID and actual duplicate/clone mapping only.'},
      {'kind':'exact_native_subtree_candidate','source_board_key':'width-768-overlay','source_step_key':'overlay','target_board_key':'width-1024-overlay','target_step_key':'overlay','include_descendants':True,'source_and_target_input_equal':True,'binding':'440px sheet and all descendant inputs match; target viewport/backdrop differ. Use observed parent scene and native IDs.'},
      {'kind':'whole_board_clone_with_declared_geometry_changes','source_board_key':'macro-docked-1280','target_board_key':'width-1600-docked','plan':'supplemental-wide-clone.json','binding':'Exact provided deltas; actual descendantIdMap and native source verification required.'}]
    result={'schema':'f02.paper.native-construction-supplement.v1','status':'PREPARED_NOT_APPLIED','file_id':'01M312VSDSZFVT45674GDVJVZN','system_version':'F02-SYSTEM/1.0.0-candidate.2','base_packet_sha256':before,'source_system_contract_sha256':hashlib.sha256(SYSTEM.encode()).hexdigest(),'source_pattern_sha256':hashlib.sha256(base.SOURCE.encode()).hexdigest(),'boards':boards,'append_to_existing':append_groups(),'clone_opportunities':hints,'paper_calls':0,'browser_calls':0}
    out=HERE/'supplemental-boards.json';out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    wide=clones.compare(base.dock_stress(),boards[-1]);wide['board_dimension_changes']={'width':{'before':1280,'after':1600}};wide['layout_exceptions']=['The primary area grows from 664 to 984px; root and primary widths, numeric column slots and chart coordinates intentionally change.','The 320px dock and 24px gap remain fixed. Reconcile source native repairs before applying a clone plan.','SVG chart geometry requires observed editable vector mapping or a bounded replacement of the actual mapped chart subtree.','Header and source semantics remain identical; new dimensions are a provisional shell evaluation, not a frozen F01 release.']
    w={'schema':'f02.paper.clone-preparation.v1','status':'LOCAL_PREPARATION_NOT_APPLIED','supplement_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'source_input_sha256':before,'pair':wide,'paper_calls':0}
    (HERE/'supplemental-wide-clone.json').write_text(json.dumps(w,ensure_ascii=False,indent=2)+'\n')
    assert hashlib.sha256(original_path.read_bytes()).hexdigest()==before
    print(json.dumps({'path':str(out),'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'base_packet_unchanged':before,'boards':len(boards),'board_steps':sum(len(b['steps']) for b in boards),'append_steps':sum(len(x['steps']) for x in result['append_to_existing']),'per_board':[{k:b[k] for k in ['key','width','height']}|{'steps':len(b['steps'])} for b in boards],'wide_clone_structure_equal':wide['input_structure_equivalent']},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
