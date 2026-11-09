(
    <div id="HBL-0" style={{ borderTopColor: '#3A4150', borderTopStyle: 'solid', borderTopWidth: '1px', boxSizing: 'border-box', display: 'flex', flexDirection: 'column', fontSynthesis: 'none', gap: '12px', maxWidth: '1000px', MozOsxFontSmoothing: 'grayscale', overflowWrap: 'anywhere', paddingTop: '20px', WebkitFontSmoothing: 'antialiased', width: '100%' }}>
      <div id="HBM-0" style={{ boxSizing: 'border-box', color: '#D7DCE3', fontFamily: '"Inter-SemiBold", "Inter", system-ui, sans-serif', fontSize: '20px', fontWeight: 600, lineHeight: '28px' }}>
        Dossier actions must open the dossier
      </div>
      <div id="HBN-0" style={{ boxSizing: 'border-box', color: '#E0A030', fontFamily: '"Inter-Regular", "Inter", system-ui, sans-serif', fontSize: '13px', lineHeight: '20px' }}>
        Proposed R4 action binding. The native workspace and Dossier sources are still draft and held in PRs #10703 and #10707. This note does not qualify or release either dependency.
      </div>
      <div id="HBO-0" style={{ boxSizing: 'border-box', color: '#A5ADBA', fontFamily: '"Inter-Regular", "Inter", system-ui, sans-serif', fontSize: '14px', lineHeight: '22px' }}>
        SectorCentralOpenCycle(nativeId, trigger) records the origin and opens Cycles. Its true return confirms navigation was accepted; it does not confirm an open or source-qualified Dossier. The new entry has cycles:null and no open Dossier state. refreshDossier reads entry.dossier.open.
      </div>
      <div id="HBP-0" style={{ boxSizing: 'border-box', color: '#A5ADBA', fontFamily: '"Inter-Regular", "Inter", system-ui, sans-serif', fontSize: '14px', lineHeight: '22px' }}>
        Extend that same entry path to carry the intended inline Dossier opening through its existing state and refreshDossier owner. Use the selected row’s admitted native ID and real trigger. Keep dossierAccess, the applied SectorCyclesApply receipt, entry/href, subject/family and publication checks before mounting. Preserve pending and unavailable states; never mount the component directly or substitute an old/default subject.
      </div>
      <div id="HBQ-0" style={{ boxSizing: 'border-box', color: '#A5ADBA', fontFamily: '"Inter-Regular", "Inter", system-ui, sans-serif', fontSize: '14px', lineHeight: '22px' }}>
        Consumer proof: start with ordered A = Energy, B = Technology while native Cycles last showed Energy. Activate Technology Dossier. Prove that the Technology component actually opens with its qualified subject, family and publication; a true navigation return does not pass. Change selection during loading and reject the obsolete opening. Pending or missing evidence must never display the Energy dossier.
      </div>
      <div id="HBR-0" style={{ boxSizing: 'border-box', color: '#A5ADBA', fontFamily: '"Inter-Regular", "Inter", system-ui, sans-serif', fontSize: '14px', lineHeight: '22px' }}>
        Use dossierOptions().onOpenCycles for the Dossier-to-Cycles action: it closes the inline Dossier and focuses sc-cycle-heading. The separate sc-cycle-return then uses the qualified Central origin. Ordered comparison and full-basis restoration remain the GPL proposal, with its existing validators and partial-result rules. Preserve G4P, BML and source/provenance holds; add no route, modal or restoration store.
      </div>
      <div id="HBS-0" style={{ boxSizing: 'border-box', color: '#9CA6B5', fontFamily: '"Inter-Regular", "Inter", system-ui, sans-serif', fontSize: '12px', lineHeight: '18px' }}>
        Source: macro / templates/si_workspace.js at 9fc460ff36345387c3a2c5435b079852e8488da0 (PR #10703). Dossier PR #10707 remains 74930f6931773b23072f91590319dc39fe5a7d07. Both were read as draft/open/unmerged. F06 extension; source inspection and Paper rendering are not native-consumer acceptance.
      </div>
    </div>
  )