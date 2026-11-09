(
    <div id="414-0" style={{ borderTopColor: 'var(--line)', borderTopStyle: 'solid', borderTopWidth: '1px', boxSizing: 'border-box', display: 'flex', flexDirection: 'column', fontSize: '12px', fontSynthesis: 'none', gap: '14px', lineHeight: '16px', MozOsxFontSmoothing: 'grayscale', overflowWrap: 'anywhere', paddingTop: '20px', WebkitFontSmoothing: 'antialiased', width: '612px' }}>
      <div id="415-0" style={{ boxSizing: 'border-box', color: 'var(--text)', fontFamily: '"Inter-SemiBold", "Inter", system-ui, sans-serif', fontSize: '20px', fontWeight: 600, lineHeight: '28px' }}>
        One feed. Different count scopes.
      </div>
      <div id="416-0" style={{ boxSizing: 'border-box', color: 'var(--text-2)', fontFamily: '"Inter-Regular", "Inter", system-ui, sans-serif', fontSize: '14px', lineHeight: '22px' }}>
        The activity strip uses supplied feed-wide report counts. Catch-up chips count story rows after row.source filtering; the review-state filter selects the visible subset. A grouped story can contain several reports. Keep these counts separate.
      </div>
      <svg xmlns="http://www.w3.org/2000/svg" width="610" height="302" viewBox="0 0 610 302" aria-label="Synthetic fixture: one qualified snapshot supplies a feed activity count of eight reports and three presented stories. Filtering to Benzinga leaves stories A and B. Mark shown reviews A and B; C stays new, so the presented-page reviewed-through receipt does not advance. The report count is never derived from review targets." id="417-0" style={{ display: 'inline-block', flexShrink: 0 }}>
        <g>
          <rect x="205.5" y="0.5" width="199" height="45" rx="8" fill="#1E222A" stroke="#3A4150" />
          <rect x="0.5" y="84.5" width="289" height="69" rx="8" fill="#1E222A" stroke="#3A4150" />
          <rect x="320.5" y="84.5" width="289" height="69" rx="8" fill="#1E222A" stroke="#3A4150" />
          <rect x="320.5" y="188.5" width="289" height="69" rx="8" fill="#1E222A" stroke="#3A4150" />
          <rect x="0.5" y="188.5" width="289" height="69" rx="8" fill="#1E222A" stroke="#3A4150" />
        </g>
        <g>
          <path d="M305 46V64H145V77M141 72L145 77L149 72M305 64H465V77M461 72L465 77L469 72M465 160V181M461 176L465 181L469 176M314 223H296M301 219L296 223L301 227" fill="none" stroke="#8B93A1" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
        </g>
        <g fontFamily="Inter" fontSize="13" fontWeight="600">
          <text x="225" y="20" fill="#D7DCE3">{"Qualified snapshot"}</text>
          <text x="16" y="107" fill="#D7DCE3">{"Feed activity"}</text>
          <text x="336" y="107" fill="#D7DCE3">{"Presented story rows"}</text>
          <text x="336" y="211" fill="#D7DCE3">{"Filter: Benzinga · New"}</text>
          <text x="16" y="211" fill="#D7DCE3">{"Mark shown"}</text>
        </g>
        <g fontFamily="Inter" fontSize="11.5">
          <text x="225" y="36" fill="#A5ADBA">{"Same ticker and editorial view"}</text>
          <text x="16" y="126" fill="#A5ADBA">{"8 reports in 24h · all sources"}</text>
          <text x="16" y="143" fill="#A5ADBA">{"Keep window, coverage and source time"}</text>
          <text x="336" y="126" fill="#A5ADBA">{"A: 3 reports · B: 2 · C: 3"}</text>
          <text x="336" y="143" fill="#A5ADBA">{"3 story rows in this fixture"}</text>
          <text x="336" y="230" fill="#A5ADBA">{"2 visible stories: A and B"}</text>
          <text x="336" y="247" fill="#A5ADBA">{"Use row.source, then review status"}</text>
          <text x="16" y="230" fill="#A5ADBA">{"A and B reviewed · C remains New"}</text>
          <text x="16" y="247" fill="#A5ADBA">{"Use presented IDs and revision pairs"}</text>
          <text x="0" y="283" fill="#A5ADBA">{"The presented-page receipt stays unchanged while C is unreviewed."}</text>
          <text x="0" y="300" fill="#A5ADBA">{"Illustrative fixture. Feed totals are supplied, never calculated from review targets."}</text>
        </g>
      </svg>
      <div id="41Y-0" style={{ boxSizing: 'border-box', color: 'var(--text-2)', fontFamily: '"Inter-Regular", "Inter", system-ui, sans-serif', fontSize: '14px', lineHeight: '22px' }}>
        Existing owners: TickerNewsPanel passes snapshot.flow to NewsFlowStrip and the complete presented rows to useNewsCatchup. Keep source-filtered counts, review-filtered visible rows, unreadShown and markShown in that hook. Do not expand source selection to arbitrary grouped-report membership.
      </div>
      <div id="41Z-0" style={{ boxSizing: 'border-box', color: 'var(--text-2)', fontFamily: '"Inter-Regular", "Inter", system-ui, sans-serif', fontSize: '14px', lineHeight: '22px' }}>
        markStoriesReviewed retains presented [sequence, item_count] pairs and the first captured evidence basis. The reviewed-through receipt advances only when every row in the current presented page is reviewed. Preserve owner, rights context and the newest stored review state.
      </div>
      <div id="420-0" style={{ boxSizing: 'border-box', color: 'var(--text-2)', fontFamily: '"Inter-Regular", "Inter", system-ui, sans-serif', fontSize: '14px', lineHeight: '22px' }}>
        Presentation extension: when a source or review filter is active, make the activity count’s scope explicit beside its existing window and coverage. This recovery specimen uses “all 2 sources” / “全部 2 个来源”. Where a scope label is needed, use “Feed total” / “资讯流总计”, derived in TickerNewsPanel from the existing selected source and effective review filter. No new count, store or review effect.
      </div>
      <div id="421-0" style={{ boxSizing: 'border-box', color: 'var(--text-2)', fontFamily: '"Inter-Regular", "Inter", system-ui, sans-serif', fontSize: '14px', lineHeight: '22px' }}>
        Acceptance: select Benzinga → two New story rows, still eight feed reports. Mark shown → only A/B reviewed and C unchanged; no full-page receipt advance. Clear the filter → C remains New. A later accepted revision of A becomes Updated without replacing its first saved basis. Repeat with the review-status filter, hidden stories, account/rights changes and current-owner readback.
      </div>
      <div id="422-0" style={{ boxSizing: 'border-box', color: 'var(--flow-muted)', fontFamily: '"Inter-Regular", "Inter", system-ui, sans-serif', fontSize: '12px', lineHeight: '18px' }}>
        Source: mastermind-terminal / terminal/components/news/&#123;TickerNewsPanel.tsx, useNewsCatchup.ts, NewsFlowStrip.tsx&#125;; terminal/lib/newsReviewState.ts. All four are byte-identical at d7a83d3348a4fcb762d93221f19c4e94cbe4505e and 8fcce1194c53543361bd21dbb2e69fc6ee556152. F04 extension; proposed presentation only. Source and Paper readback do not establish browser or production acceptance.
      </div>
    </div>
  )