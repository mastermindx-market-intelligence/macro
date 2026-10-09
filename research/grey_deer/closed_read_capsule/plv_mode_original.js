function _plvMode(d, et){
  /* 1. Weekends, the overnight hours, and everything after the nightly build has
        settled the day: "Forming today" has nothing to say, so the strip is not
        rendered at all. The upper bound is the nightly handoff, NOT midnight — past it
        the board below carries the answer and a pending-verdict strip would contradict
        it. (The spec's own §6.2 rule 1 upper bound of 16:20 made rule 3 unreachable;
        this is the bound that keeps rule 3 alive without inventing a false-tense
        window.) */
  if(et.wd==='Sat'||et.wd==='Sun') return null;
  if(et.min<PLV_WAKE||et.min>=PLV_SETTLE) return null;
  if(!d||!d.meta) return null;
  /* 2. A frozen file must NEVER present as today — but the strip must not GUESS why.
        Before today's first pass is even due it is not a fault at all, so say nothing;
        after that, name the observable fact and not a cause we cannot see (m1). */
  if(d.meta.session_et&&d.meta.session_et!==et.ymd){
    if(et.min<PLV_FIRST) return null;
    return {mode:'dark', why:'none_today'};
  }
  /* 3. Post-close. Deliberately AHEAD of the age gates: without this rule the
        15-minute staleness gate fires every single evening and the strip lies
        "prices aren't updating" after every close — a nightly lie, not an edge case.
        But it must not launder a fault either, so the last pass has to have landed
        near the close for the frozen rows to be describing it (m2). */
  if(et.min>PLV_SHUT){
    var cms=_plvTsMin(d.meta.pass_ts);
    if(d.status!=='dark'&&cms!==null&&cms>=PLV_CLOSE_PASS) return {mode:'closed', why:null};
    return {mode:'dark', why:(d.reason==='no_pack'?'no_pack':(d.reason==='stale_pack'?'stale_pack':'quotes'))};
  }
  /* 4. The producer itself declined to speak — this is the one cause it ATTESTS. */
  if(d.status==='dark') return {mode:'dark', why:(d.reason==='no_pack'?'no_pack':(d.reason==='stale_pack'?'stale_pack':'quotes'))};
  /* 5. Three missed passes — the file is no longer describing the current tape. Not
        before the day's first pass is due, though: late is not broken (m1). */
  var pms=Date.parse(d.meta.pass_ts||'');
  if(isFinite(pms)&&(Date.now()-pms)>PLV_MAXAGE&&et.min>=PLV_FIRST) return {mode:'dark', why:'quotes'};
  /* 6. Speaking a confident "quiet tape" while more than half the armed names are
        unreadable is degraded-ships-confident. */
  var dc=d.meta.dark_counts||{}, sum=0, k;
  for(k in dc){ if(Object.prototype.hasOwnProperty.call(dc,k)) sum+=Number(dc[k])||0; }
  var ev=Number(d.meta.evaluated_n);
  if(isFinite(ev)&&ev>0&&(sum/ev)>=0.5) return {mode:'dark', why:'quotes'};
  return {mode:'live', why:null};   /* refined to 'quiet' once rows are known */
}
