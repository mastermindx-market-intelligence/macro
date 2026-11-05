/* Device-local Government Revenue briefcase controls.
 *
 * The state/alert/export contract lives in government-revenue-briefcase.js.
 * This file only mounts that contract onto the page and never performs remote
 * delivery, polling, or account synchronization.
 */
(function(root){
  'use strict';

  root.mountGovernmentRevenueBriefcaseUI=function(api){
    var briefcase=null,selectedView='',bound=false,ownerId='';
    var get=api.get,tr=api.tr,esc=api.esc,text=api.text;
    // The page's existing identity owner supplies the authenticated subject.
    // No storage read occurs before that callback. Unassigned legacy bytes stay untouched.
    function setOwner(next){
      next=typeof next==='string'&&/^[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}$/.test(next)?next:'';
      if(next===ownerId&&briefcase)return;
      ownerId=next;selectedView='';briefcase=null;
      if(typeof api.clearPrivatePresentation==='function')api.clearPrivatePresentation();
      if(ownerId){try{briefcase=root.createGovernmentRevenueBriefcase({storage:root.localStorage,ownerId:ownerId,resolveEventIds:api.getMatchingEventIds})}catch(error){briefcase=null}}
      bind();render();
    }


    function status(copy,warn){var el=get('briefcaseStatus');if(!el)return;el.className='briefcase-status'+(warn?' warn':'');el.textContent=copy}
    function typeLabel(type){return{opportunity:tr('Opportunity change','机会变化'),award_change:tr('Award / action change','授标 / 行动变化'),recompete:tr('Derived expiry watch','推导到期观察')}[type]||tr('Other change','其他变化')}
    /* Alert receipts are written to device storage the moment they fire, so a message
       translated at write time would freeze the language it was written in. Copy is
       resolved HERE, at render time, from the stored type; the strings the state layer
       persists stay untouched and only stand in for a type this build does not know. */
    function alertText(item){
      if(item.notification_kind==='correction')return{
        message:tr('Correction to a previously observed matching record.','先前已观测的匹配记录发生修正。'),
        warning:tr('A prior observation was revised; this is not a new award, obligation or issuer revenue.','先前观测已修订；这不代表新增授标、义务额或发行人收入。')
      };
      if(item.notification_kind!=='new_observation')return{
        message:tr('Previously saved local alert; whether this was new information or a correction was not retained.','历史本地提醒：未保留其属于新信息还是修正的分类。'),
        warning:item.type==='recompete'?tr('Worked out from contract dates — not an official recompete date or solicitation.','根据合同日期推算——非官方重新竞标日期或招标公告。'):null
      };
      var byType={opportunity:{message:tr('New matching opportunity.','发现新的匹配机会。'),warning:null},award_change:{message:tr('New matching award or action change.','发现新的授标或行动变化。'),warning:null},recompete:{message:tr('New matching expiry watch.','发现新的到期观察。'),warning:tr('Worked out from contract dates — not an official recompete date or solicitation.','根据合同日期推算——非官方重新竞标日期或招标公告。')}}[item.type];return byType||{message:text(item.message),warning:item.warning||null}}
    function selectedAlert(){if(!briefcase||!selectedView)return null;var type=get('alertType').value;return briefcase.listAlerts().find(function(row){return row.view_id===selectedView&&row.type===type})||null}

    function render(message,warn){
      var select=get('savedViewSelect'),toggle=get('toggleLocalAlert'),remove=get('deleteView');
      if(!select||!toggle||!remove)return;
      ['savedViewName','saveView','alertType','localInbox'].forEach(function(id){get(id).disabled=!briefcase});
      if(!briefcase){
        select.innerHTML='';select.value='';get('savedViewName').value='';get('localInboxCount').textContent='0';
        select.disabled=true;toggle.disabled=true;remove.disabled=true;get('exportViewJson').disabled=true;get('exportViewCsv').disabled=true;
        status(tr('Sign in to use your saved research on this device.','登录后可使用此设备上属于您的已保存研究。'),true);return;
      }
      select.disabled=false;get('exportViewJson').disabled=false;get('exportViewCsv').disabled=false;
      var views=briefcase.listViews();
      if(selectedView&&!views.some(function(view){return view.id===selectedView}))selectedView='';
      select.innerHTML='<option value="">'+esc(tr('Current unsaved view','当前未保存视图'))+'</option>'+views.map(function(view){return'<option value="'+esc(view.id)+'">'+esc(view.name)+'</option>'}).join('');
      select.value=selectedView;
      var view=selectedView?briefcase.getView(selectedView):null;
      get('savedViewName').value=view?view.name:'';remove.disabled=!view;toggle.disabled=!view||!!(view.cut&&view.cut.contract==='government_revenue_saved_identity.v1');
      var alert=selectedAlert();
      toggle.textContent=alert&&alert.enabled?tr('Disable local alert','停用本地提醒'):tr('Enable local alert','启用本地提醒');
      get('localInboxCount').textContent=briefcase.listInbox().length;
      status(message!=null?message:tr('Saved views and alerts stay in this browser. Alerts are checked only when you open or refresh this page.','保存的视图和提醒仅保留在此浏览器中。提醒仅在打开或刷新此页面时检查。'),warn===true);
    }

    function selectedEventId(){
      return typeof api.getSelectedEventId==='function'?api.getSelectedEventId():null;
    }

    function savedSource(value){
      try{var url=new URL(value);if(url.protocol!=='https:'||url.username||url.password||url.port&&url.port!=='443')return null;return url.href}catch(error){return null}
    }

    function factLabel(fact){var code=fact.label_code||fact.semantic||fact.id;return typeof api.factLabel==='function'?api.factLabel(code):text(code)}

    function openSavedCut(view,cut){
      var payload=cut.payload,meta=payload.workspace,records=payload.records,ownerAtOpen=ownerId;
      var copy=tr('Device-local saved evidence window, not the current workspace. Source clocks and revisions below are the values retained at save time.','这是设备本地保存的证据窗口，并非当前工作区。下列来源时钟与修订版本均为保存时保留的值。');
      var clocks=tr('Evidence date: ','证据日期：')+text(meta.as_of)+'\n'+tr('Known to Mastermind: ','Mastermind 获知时间：')+text(meta.known_at)+'\n'+tr('Source build: ','来源构建时间：')+(meta.generated_at?text(meta.generated_at):tr('Not retained','未保留'))+'\n'+tr('Device copy: ','设备副本时间：')+text(payload.exported_at)+'\n'+tr('Workspace: ','工作区：')+text(meta.bundle_id)+'\n'+tr('Saved filters: ','保存的筛选：')+JSON.stringify(payload.query.filters);
      var coverage=meta.coverage||{},unknown=tr('not retained','未保留');
      var scope=tr('Retained matching records: ','保留的匹配记录：')+records.length+' · '+tr('Source window: ','来源窗口：')+(coverage.events_visible==null?unknown:coverage.events_visible)+' / '+(coverage.events_available_before_cap==null?unknown:coverage.events_available_before_cap)+' · '+tr('Source cap: ','来源上限：')+(coverage.event_cap==null?unknown:coverage.event_cap)+' · '+tr('Freshness at save: ','保存时的新鲜度：')+text((meta.freshness||{}).status,unknown);
      var limitations=(Array.isArray(meta.limitations)?meta.limitations:[]).map(function(value){return'<li>'+esc(value)+'</li>'}).join('');
      var html='<p class="limit-copy">'+esc(scope)+'</p><p class="limit-copy">'+esc(copy)+'</p><div class="receipt-code">'+esc(clocks).replace(/\n/g,'<br>')+'</div>'+(limitations?'<ul class="limit-copy">'+limitations+'</ul>':'')+'<p class="limit-copy">'+esc(tr('Amounts retain their source meanings; they are not issuer revenue. Freshness was recorded at capture, not re-certified today.','金额保留原始来源含义，不代表发行人收入。新鲜度为保存时记录，并非今日重新核验。'))+'</p><button class="tool-btn" id="savedCutDownload" type="button">'+esc(tr('Export this saved JSON','导出此保存窗口 JSON'))+'</button>';
      html+=records.map(function(event){
        var selected=event.event_id===cut.selected_event_id;
        var facts=Array.isArray(event.amounts)?event.amounts:[],amount=facts.find(function(row){return row.id===event.primary_amount_id});
        var dates=Array.isArray(event.dates)?event.dates:[],date=dates.find(function(row){return row.id===event.primary_date_id});
        var receipt=Array.isArray((event.evidence||{}).receipts)?event.evidence.receipts.find(function(row){return savedSource(row.url)}):null;
        var title=tr(event.title_original||event.title_zh||event.event_id,event.title_zh||event.title_original||event.event_id);
        var details=tr('Event: ','事件：')+text(event.event_id)+'\n'+tr('Record: ','记录：')+text(event.record_id)+' · '+tr('Revision ','修订 ')+text(event.version)+'\n'+tr('Observation known at: ','观测获知时间：')+text((event.change||{}).known_at);
        if(amount)details+='\n'+factLabel(amount)+': '+text(amount.value)+' '+text(amount.currency)+(amount.as_of?' · '+tr('as of ','截至 ')+text(amount.as_of):'')+(amount.known_at?' · '+tr('known ','获知 ')+text(amount.known_at):'');
        if(date)details+='\n'+factLabel(date)+': '+text(date.value);
        return'<article class="receipt" data-saved-cut-event="'+esc(event.event_id)+'"'+(selected?' data-saved-cut-selected="true" tabindex="-1"':'')+'><div class="receipt-kind">'+esc(typeLabel(event.kind))+(selected?' · '+esc(tr('Selected at save','保存时所选')):'')+((event.change||{}).is_correction===true?' · '+esc(tr('Correction','修正')):'')+'</div><h3>'+esc(title)+'</h3><div class="receipt-code">'+esc(details).replace(/\n/g,'<br>')+'</div>'+(receipt?'<a href="'+esc(savedSource(receipt.url))+'" target="_blank" rel="noopener noreferrer">'+esc(tr('Original source','原始来源'))+'</a>':'')+'</article>';
      }).join('');
      if(!records.length)html+='<p class="limit-copy">'+esc(tr('No matching records were retained in this original window. This does not describe the current source.','此原始窗口中没有匹配记录。这并不描述当前来源状态。'))+'</p>';
      api.openDrawer({title:tr('Saved evidence window · ','保存的证据窗口 · ')+view.name,html:html,focus:get('savedViewSelect')});
      var button=root.document.getElementById&&root.document.getElementById('savedCutDownload');
      if(button)button.addEventListener('click',function(){
        if(ownerId!==ownerAtOpen||!briefcase)return;
        var bundle=text(meta.bundle_id).replace(/[^A-Za-z0-9._-]/g,'_');
        var ok=download('government-revenue-saved-cut-'+bundle+'.json',JSON.stringify(cut,null,2)+'\n','application/json;charset=utf-8');
        status(ok?tr('Original saved evidence window exported.','已导出原始保存证据窗口。'):tr('The saved export is unavailable in this browser.','此浏览器无法导出保存窗口。'),!ok);
      });
      var target=typeof root.document.querySelector==='function'?root.document.querySelector('[data-saved-cut-selected="true"]'):null;
      if(target){if(typeof target.scrollIntoView==='function')target.scrollIntoView({block:'nearest'});if(typeof target.focus==='function')target.focus({preventScroll:true})}
    }

    function openSavedIdentity(view,cut){
      var subject=cut.subject,record=cut.record,context=record.archetype_context,ownerAtOpen=ownerId;
      function meaning(value){
        var labels={not_established:tr('Not established','尚未确立'),unknown:tr('Unknown','未知'),
          ordinary_share:tr('Ordinary share','普通股'),adr:tr('ADR / depositary receipt','ADR / 存托凭证'),
          joint_venture:tr('Joint venture','合资企业'),equity_method:tr('Equity method','权益法'),
          consolidated:tr('Consolidated basis disclosed','已披露合并口径'),
          source_supported_current_research:tr('Source-supported current research identity','来源支持的当前研究身份'),
          government_revenue_identity_context:tr('Government Revenue identity context only','仅用于政府收入研究的身份背景'),
          current_observation_only:tr('Current observation only','仅为当前观测'),
          disclosed_snapshot_only:tr('Disclosure snapshot only; later continuity is unestablished','仅为披露快照；其后持续性尚未确立'),
          direct_edge_interest_not_issuer_capture:tr('Direct ownership interest, not issuer revenue or cash capture','直接所有权权益，不代表发行人收入或现金获取')};
        return Object.prototype.hasOwnProperty.call(labels,value)?labels[value]:text(value,tr('Not established','尚未确立'));
      }
      function fields(lines,source,spec){spec.forEach(function(field){if(source[field[0]]!=null)lines.push(tr(field[1],field[2])+meaning(source[field[0]]))})}
      function interest(value){return typeof value==='number'&&Number.isFinite(value)?Math.round(value*1000)/10+'%':meaning(value)}
      var lines=[tr('Subject: ','主体：')+subject.ticker+' · '+record.company_name,
        tr('Evidence content ID: ','证据内容标识：')+cut.atlas.content_id,
        tr('Context known at: ','背景获知时间：')+subject.known_at,
        tr('Source observation known at: ','来源观测获知时间：')+subject.observation_known_at,
        tr('Research identity known at: ','研究身份获知时间：')+text(subject.research_identity_known_at,tr('Not established','尚未确立')),
        tr('Source build: ','来源构建时间：')+cut.atlas.generated_at,
        tr('Device copy: ','设备副本时间：')+cut.saved_at,
        tr('Saved filters: ','保存的筛选：')+JSON.stringify(cut.filters)];
      var html='<p class="limit-copy">'+esc(tr('Original device-local source context. This is not the current source, award coverage, revenue capture or trading authority. Current-source navigation remains pinned separately.','原始设备本地来源背景。这并非当前来源、授标覆盖、收入获取或交易权限。当前来源导航另行绑定证据截点。'))+'</p><div class="receipt-code">'+esc(lines.join('\n')).replace(/\n/g,'<br>')+'</div><p class="limit-copy">'+esc(tr(record.attribution_reason_en,record.attribution_reason_zh||record.attribution_reason_en))+'</p>';
      context.listing_cases.concat(context.ownership_cases).forEach(function(row){
        var native=row.native_identity||{},research=row.research_identity||{};
        var details=[tr('Source known at: ','来源获知时间：')+row.known_at,
          tr('Source period: ','来源期间：')+text(row.source_as_of,tr('Not established','尚未确立')),
          tr('Effective interval: ','有效区间：')+meaning(row.effective_interval_state),
          tr('Source reuse rights: ','来源复用权利：')+meaning(row.rights_state)];
        fields(details,native,[['issuer_name_as_printed','Issuer as printed: ','来源原文发行人：'],
          ['issuer_registry','Issuer registry: ','发行人登记机关：'],['issuer_native_id','Native issuer identifier: ','原生发行人标识：'],
          ['venue','Venue: ','交易场所：'],['symbol','Source symbol: ','来源代码：'],['security_kind','Security type: ','证券类型：']]);
        if(row.ordinary_shares_per_adr!=null)details.push(tr('Ordinary shares per ADR: ','每份 ADR 对应普通股：')+row.ordinary_shares_per_adr);
        if(row.quote_currency)details.push(tr('Quote currency: ','报价币种：')+row.quote_currency);
        fields(details,research,[['state','Research identity: ','研究身份：'],['scope','Research scope: ','研究范围：'],
          ['issuer_cik','SEC filer CIK: ','SEC 披露主体 CIK：'],['filer_name_as_printed','SEC filer as printed: ','SEC 来源原文披露主体：'],
          ['security_isin','Security ISIN: ','证券 ISIN：'],['underlying_isin','Underlying ISIN: ','标的普通股 ISIN：'],
          ['underlying_symbol_as_printed','Underlying source symbol: ','标的来源代码：'],['underlying_venue_as_printed','Underlying source venue: ','标的来源交易场所：'],
          ['depositary_as_printed','Depositary as printed: ','来源原文存托行：'],['sponsorship_as_printed','Sponsorship source code: ','来源保荐状态代码：'],
          ['mapping_snapshot','Identity observation date: ','身份观测日期：'],['known_at','Research identity known at: ','研究身份获知时间：'],
          ['effective_interval_state','Research validity: ','研究有效性：']]);
        if(row.relationship){
          fields(details,row,[['relationship','Ownership relationship: ','所有权关系：'],['interest_basis','Interest basis: ','权益口径：'],['accounting_basis','Accounting basis: ','会计口径：']]);
          details.push(tr('Ownership interest: ','所有权权益：')+interest(row.ownership_interest));
          (row.documentary_counterparties||[]).forEach(function(party){details.push(tr('Same-source counterparty: ','同一来源的交易对方：')+text(party.name_as_printed)+' · '+interest(party.ownership_interest)+' · '+tr('Identity path: ','身份路径：')+meaning(party.identity_path))});
          details.push(tr('Revenue / workshare / cash capture: ','收入 / 工作份额 / 现金获取：')+[row.revenue_capture,row.workshare,row.cash_capture].map(meaning).join(' / '),
            tr('Ownership interest is not revenue, workshare or distributable cash.','所有权权益不等于收入、工作份额或可分配现金。'));
        }
        details.push(tr('Listing admission / price comparability / recipient attribution / economic capture: ','上市准入 / 价格可比性 / 收款方归属 / 经济获取：')+[row.listing_admission,row.price_comparability,row.recipient_attribution,row.economic_capture].map(meaning).join(' / '));
        html+='<article class="receipt"><h3>'+esc(native.symbol||row.canonical_name||subject.ticker)+'</h3><div class="receipt-code">'+esc(details.join('\n')).replace(/\n/g,'<br>')+'</div>'+row.evidence.map(function(receipt){var url=savedSource(receipt.url);return url?'<a class="source-link" href="'+esc(url)+'" target="_blank" rel="noopener noreferrer">'+esc(receipt.publisher+' · '+receipt.record_id)+'</a><div class="receipt-code">'+esc(receipt.content_sha256)+'</div>':''}).join('')+'</article>';
      });
      if(context.gaps.length)html+='<p class="limit-copy">'+esc(context.gaps.join(' · '))+'</p>';
      html+='<button class="tool-btn" id="savedIdentityJson" type="button">'+esc(tr('Export this saved JSON','导出此保存窗口 JSON'))+'</button> <button class="tool-btn" id="savedIdentityCsv" type="button">'+esc(tr('Export this saved CSV','导出此保存窗口 CSV'))+'</button>';
      api.openDrawer({title:tr('Saved source context · ','保存的来源背景 · ')+view.name,html:html,focus:get('savedViewSelect')});
      [['savedIdentityJson','json'],['savedIdentityCsv','csv']].forEach(function(pair){
        var button=root.document.getElementById&&root.document.getElementById(pair[0]);
        if(button)button.addEventListener('click',function(){if(ownerId===ownerAtOpen&&briefcase)exportSavedIdentity(view.id,pair[1])});
      });
    }

    function exportSavedIdentity(id,kind){
      var output=briefcase.buildSavedResearchExport(id,kind),ok=download(output.filename,output.content,output.media_type);
      status(ok?tr('Original saved source context exported. No current data was substituted.','已导出原始保存来源背景，未替换为当前数据。'):tr('The saved export is unavailable in this browser.','此浏览器无法导出保存窗口。'),!ok);
    }

    function applySaved(){
      if(!briefcase)return;
      var view=briefcase.getView(get('savedViewSelect').value);selectedView=view?view.id:'';
      if(!view){render();return}
      var retained=briefcase.getSavedCut(view.id);
      if(!retained.ok&&retained.reason!=='cut_not_captured'){
        render(tr('The original saved evidence window could not be verified. Current data was not substituted.','无法核验原始保存证据窗口，未以当前数据替代。'),true);return;
      }
      if(retained.ok&&retained.cut.contract==='government_revenue_saved_identity.v1'){
        if(typeof api.applyResearchContext==='function')api.applyResearchContext(retained.cut);
        openSavedIdentity(view,retained.cut);
        render(tr('Original saved source context reopened; current source may differ or be unavailable.','已重新打开原始保存来源背景；当前来源可能不同或不可用。'),false);return;
      }
      api.applyFilters(view.filters||{});
      if(retained.ok){
        openSavedCut(view,retained.cut);
        render(tr('Original saved window reopened. See the page for current source coverage.','已重新打开原始保存窗口；当前来源覆盖情况请参阅页面。'),false);
      }else render(tr('Saved filters applied. This older view did not retain an original evidence window.','已应用保存筛选。此历史视图未保留原始证据窗口。'),true);
    }

    function save(){
      if(!briefcase)return;
      var name=get('savedViewName').value.trim();
      if(!name){status(tr('Name the current view before saving it.','请先为当前视图命名。'),true);get('savedViewName').focus();return}
      try{
        var filters=api.getFilters(),input={name:name,filters:filters},ownerAtSave=ownerId,storeAtSave=briefcase;
        if(filters.mode==='companies'&&typeof api.getResearchContext==='function'){
          var context=api.getResearchContext();
          if(context!==undefined)input.research_context=context;
        }
        if(ownerAtSave!==ownerId||storeAtSave!==briefcase)return;
        if(['changes','awards','opportunities','recompetes'].indexOf(filters.mode||'changes')>=0&&typeof api.getWorkspace==='function'){
          input.workspace=api.getWorkspace();input.readiness={complete:api.isWorkspaceReady()===true,bundle_matched:api.isWorkspaceReady()===true};
          input.visible_event_ids=typeof api.getVisibleEventIds==='function'?api.getVisibleEventIds():null;
          input.selected_event_id=selectedEventId();
        }
        var result=selectedView?briefcase.updateView(selectedView,input):briefcase.createView(input);
        selectedView=result.view.id;
        render(result.persisted?(result.view.cut?tr('View and original evidence window saved on this device.','视图及原始证据窗口已保存在此设备。'):tr('Filters saved on this device; no original evidence window was captured for this view.','筛选已保存在此设备；此视图未保存原始证据窗口。')):tr('View is available for this tab, but browser storage is unavailable.','视图可在此标签页使用，但浏览器存储不可用。'),!result.persisted);
      }catch(error){
        if(error&&error.code==='saved_cut_too_large')status(tr('Refine the filters before saving this evidence window: at most 100 records and 256 KiB. Nothing was truncated or saved.','请先缩小筛选范围：证据窗口最多包含 100 条记录、256 KiB。未截断或保存任何内容。'),true);
        else if(error&&error.code==='unsupported_view_mode')status(tr('Saving is not available in this view. Choose Changes, Award activity, Opportunities, Recompete watch or Company collection scope.','此视图暂不支持保存。请选择变化、授标动态、机会、再竞争观察或公司采集范围。'),true);
        else if(error&&error.code==='saved_view_has_alerts')status(tr('This saved view has local alerts. Select Current unsaved view and save the source context separately; existing alerts were preserved.','此保存视图包含本地提醒。请选择当前未保存视图，将来源背景单独保存；现有提醒已保留。'),true);
        else if(error&&error.code==='research_context_unavailable'||error&&error.code==='invalid_saved_cut')status(tr('The selected source context is unavailable or changed. Nothing was saved or substituted.','所选来源背景不可用或已变化。未保存或替换任何内容。'),true);
        else if(error&&error.code==='workspace_not_ready')status(tr('Wait for the complete verified workspace before saving its original evidence window.','请等待完整且已核验的工作区加载后，再保存原始证据窗口。'),true);
        else status(tr('This view could not be saved.','无法保存此视图。'),true);
      }
    }

    function remove(){
      if(!briefcase||!selectedView)return;
      var result=briefcase.deleteView(selectedView);selectedView='';
      render(result.deleted?tr('Saved view and its local alerts were deleted.','已删除保存视图及其本地提醒。'):tr('Saved view was not found.','未找到保存视图。'),!result.deleted);
    }

    function reconcile(announce){
      if(!briefcase||!api.isWorkspaceReady())return null;
      var result=briefcase.reconcile(api.getWorkspace(),{complete:true,bundle_matched:true});
      if(!result.reconciled){render(tr('Local alert check unavailable. Existing baselines and receipts were preserved.','本地提醒检查暂不可用。已保留现有基线和凭证。'),true);return result;}
      var copy=result.alerts.length?result.alerts.length+tr(' new local alert receipts.',' 条新的本地提醒凭证。'):result.withheld_alert_ids.length?tr('Award-change alert baseline withheld: the official award rail is unavailable.','授标变化提醒基线已暂停：官方授标链路不可用。'):announce?tr('Local alert baseline checked against the complete governed workspace.','已根据完整受治理工作区检查本地提醒基线。'):null;
      if(result.rebaselined_alert_ids&&result.rebaselined_alert_ids.length)copy=(copy?copy+' ':'')+tr('Saved alert windows updated to match the page. Existing records were baselined without new alerts.','已更新保存的提醒窗口以匹配页面。现有记录已纳入基线，未生成新提醒。');
      if(!result.persisted)copy=(copy?copy+' ':'')+tr('Alert changes are available only in this tab; browser storage is unavailable.','提醒变化仅在此标签页可用；浏览器存储不可用。');
      render(copy,!result.persisted||!!result.withheld_alert_ids.length);return result;
    }

    function toggleAlert(){
      if(!briefcase||!selectedView)return;
      var view=briefcase.getView(selectedView);if(view&&view.cut&&view.cut.contract==='government_revenue_saved_identity.v1')return;
      var alert=selectedAlert();
      try{
        var changed=alert?briefcase.updateAlert(alert.id,{enabled:!alert.enabled}):briefcase.createAlert({view_id:selectedView,type:get('alertType').value});
        var result=reconcile(true);
        if(!changed.persisted&&result&&!result.reconciled)render(tr('Alert changes are available only in this tab; browser storage is unavailable. The local alert check could not complete.','提醒变化仅在此标签页可用；浏览器存储不可用。本地提醒检查未能完成。'),true);
        if(!result)render(changed.persisted?tr('Local alert saved. Its first baseline will be established after the complete workspace loads.','本地提醒已保存。完整工作区加载后将建立首次基线。'):tr('Alert changes are available only in this tab; browser storage is unavailable.','提醒变化仅在此标签页可用；浏览器存储不可用。'),!changed.persisted);
      }catch(error){status(tr('This local alert could not be changed.','无法更改此本地提醒。'),true)}
    }

    function openInbox(){
      if(!briefcase)return;
      var rows=briefcase.listInbox(),html=rows.map(function(item){var ac=alertText(item);return'<article class="receipt"><div class="receipt-kind">'+esc(typeLabel(item.type))+'</div><h3>'+esc(item.title||item.event_id)+'</h3><p>'+esc(ac.message)+(ac.warning?'<br><strong>'+esc(ac.warning)+'</strong>':'')+'</p><div class="receipt-code">'+esc('event_id: '+text(item.event_id)+'\nobserved_at: '+text(item.observed_at)+'\nworkspace: '+text(item.workspace_bundle_id))+'</div></article>'}).join('')||'<div class="empty-state"><div><span class="empty-mark" aria-hidden="true">○</span><strong>'+esc(tr('No local alert receipts','暂无本地提醒凭证'))+'</strong><p>'+esc(tr('The first complete-workspace check establishes a baseline and never backfills historical alerts.','首次完整工作区检查仅建立基线，绝不回填历史提醒。'))+'</p></div></div>';
      api.openDrawer({title:tr('Local research inbox','本地研究收件箱'),html:html,focus:root.document.activeElement});
    }

    function download(filename,content,mediaType){
      try{var blob=new Blob([content],{type:mediaType}),href=URL.createObjectURL(blob),link=root.document.createElement('a');link.href=href;link.download=filename;root.document.body.appendChild(link);link.click();link.remove();URL.revokeObjectURL(href);return true}catch(error){return false}
    }

    function exportView(kind){
      if(!briefcase)return;
      try{
        if(selectedView){var view=briefcase.getView(selectedView);if(view&&view.cut&&view.cut.contract==='government_revenue_saved_identity.v1'){exportSavedIdentity(selectedView,kind);return}}

        if(kind==='csv'){
          var csv=briefcase.buildCsvExport(api.getWorkspace(),api.getFilters()),csvOk=download(csv.filename,csv.content,csv.media_type);
          status(csvOk?tr('Auditable CSV view exported.','已导出可审计的 CSV 视图。'):tr('CSV export is unavailable in this browser.','此浏览器无法导出 CSV。'),!csvOk);return;
        }
        var payload=briefcase.buildJsonExport(api.getWorkspace(),api.getFilters()),day=text((payload.workspace||{}).as_of,'undated').replace(/[^0-9-]/g,''),bundle=text((payload.workspace||{}).bundle_id,'unversioned').replace(/[^A-Za-z0-9._-]/g,'_'),content=JSON.stringify(payload,null,2)+'\n',jsonOk=download('government-revenue-'+day+'-'+bundle+'-view.json',content,'application/json;charset=utf-8');
        status(jsonOk?tr('Auditable JSON view exported.','已导出可审计的 JSON 视图。'):tr('JSON export is unavailable in this browser.','此浏览器无法导出 JSON。'),!jsonOk);
      }catch(error){
        if(error&&error.code==='unsupported_export_mode'){
          status(tr('Export is not available for this view. Switch to Changes, Award activity, Opportunities or Recompete watch to export.','此视图暂不支持导出。请切换到变化、授标动态、机会或再竞争观察后导出。'),true);return;
        }
        status(tr('The governed view could not be exported.','无法导出受治理视图。'),true);
      }
    }

    function bind(){
      if(bound||!briefcase){render();return}bound=true;
      get('savedViewSelect').addEventListener('change',applySaved);get('saveView').addEventListener('click',save);
      get('savedViewName').addEventListener('keydown',function(event){if(event.key==='Enter'){event.preventDefault();save()}});
      get('deleteView').addEventListener('click',remove);get('alertType').addEventListener('change',function(){render()});
      get('toggleLocalAlert').addEventListener('click',toggleAlert);get('localInbox').addEventListener('click',openInbox);
      get('exportViewJson').addEventListener('click',function(){exportView('json')});get('exportViewCsv').addEventListener('click',function(){exportView('csv')});
    }

    if(typeof api.onOwnerChange==='function')api.onOwnerChange(setOwner);
    return{bind:bind,render:render,reconcile:reconcile,setOwner:setOwner,get available(){return !!briefcase}};
  };
})(window);
