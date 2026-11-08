from pathlib import Path
import json,collections
root=Path(__file__).resolve().parents[1]
# Each row maps a source-backed capability to a reachable candidate/owned successor.
rows=[
('Exact root and listing identity','OptionsWorkspace; D08 listing object','IMPROVE','B01/B03/B17; existing root validator','Keep root, namespace, venue/security where established; no ticker-only joins','D08 / incumbent identity'),
('PRISM and GEX query aliases','OptionsWorkspace; GexDeskView','RETAIN','Existing parser: prism→gex; strike/expiry/matrix/chart','Legacy links and Back/Forward survive; explicit valid view wins','D08 route owner'),
('GEX strike and expiry breakdowns','GexDeskView; Exposure R2 1GO5-0','RETAIN','B01 By strike / By expiry; B10 Research','Preserve detailed profiles behind explicit reachable controls','Incumbent GEX reader'),
('Strike × expiry heatmap','ExposureMap; p-V-0 / 1GO5-0','IMPROVE','B01/B02/B06/B11','Keep signed cells, exact ISO coordinates and density; readable selection','Qualified projection'),
('Spot marker and reference','GEX/Exposure R2/Levels','RETAIN','B01/B02/B14','Spot and its timestamp remain separate from source book time','Quote and book owners'),
('Strike/expiry marginal graphics','Exposure R2 p-V-0','RELOCATE','B01 numeric totals + By strike/By expiry; B10','Keep full analytical breakdown; quieter primary composition does not delete it','D08B incumbent breakdown components'),
('Node inspector','ExposureMap; Exposure R2','IMPROVE','B01/B03','Separate aggregate from contracts, selected expiry from strike subtotal','Source member resolver'),
('Exact contract resolution','D08 pin interface; optionsContractShortlist.ts','IMPROVE','B03→B17→C-owned Plan','Actual source row and C validation precede a pin; ambiguity is inspectable','D08C / incumbent resolver'),
('Source clock distinctions','GEX/archive/matrix/vol adapters','IMPROVE','B01/B02/B03/B13/B15','Keep spot/OI position/report/availability/build dates separate','Incumbent source producers'),
('Expiry/range/lens selection','ExposureMap/ExposureSurface','IMPROVE','B01/B02/B05/B06/B10/B11','Preserve selected identity across filters; no nearest-node substitution','D08 common state'),
('Matrix color normalization','ExposureMap; served matrix','RETAIN','B01 legend and source contract','Retain declared P95/square-root scope; not replaced by Surface tier scale','Existing matrix model'),
('Partial totals and finite zero','ExposureMap; served matrix','IMPROVE','B01/B02/B11/B15','Known subtotal distinct from complete total; zero distinct from null','Qualified projection'),
('Coverage denominators','Exposure readers; source expected may be null','IMPROVE','B01/B02/B03/B11/B15','Grid and reported-row completeness do not establish source collection coverage','Source coverage owner'),
('Matched observation comparison','exposureReportedChange.ts; R2 compare 1I64-0','IMPROVE','B07/B16','Global finite cohort, method/time gates; signed/gross/magnitude distinct','Incumbent comparison coordinator'),
('Reported and qualification differences','exposureReportedChange.ts','IMPROVE','B16','Show prior/current-only and gained/lost separately from matched change','Incumbent comparator'),
('Full-lens versus displayed totals','exposureSurface.ts','RETAIN','B01/B05/B06; Source & calculations','Crop does not silently redefine full-lens totals; unknown constituent keeps total unknown','Qualified projection'),
('Dated book archive and history','gex_dates / gex_at; R2 1HWG-0','RETAIN','B01 Book history; B10','Preserve source date and separate current quote/history context','Incumbent archive owner'),
('Replay reference','R2 replay; D08 replay object','RELOCATE','B01/B10→existing validated replay/archival destination','B presents exposure archive; D/incumbent owner handles temporal admission/cursor','D08D and incumbent archive'),
('Review/scenario and compare-plan access','ExposureMap Review/Scenario; R2 1IIV-0/1IN4-0','RELOCATE','Existing review/scenario owner; C Plan after qualification','No duplicated plan, payoff, saved-scenario or compare-plan screen','D08C; B presentation only'),
('Price context and GEX profile','GexDeskView; R2 1H4T-0','RETAIN','B01 Price context; B10 Research','Keep repriced curve, source parameters and sampled grid identity','Macro/Terminal GEX owner'),
('Walls, gamma flip and max pain','gex_engine.py/gex_model.py; GEX/Levels','RETAIN','B14 price map + existing detail controls','Exact price anchors and no-crossing null survive; keep method definitions','Incumbent producers'),
('Gamma regime assumption passport','gex_engine.py','IMPROVE','Source & calculations; B14 Unknown state','Model convention is not observed dealer inventory; null stays unknown','GEX/Levels producer'),
('Expected move and volatility bands','gex_model.py; moves source','RETAIN','Price/Positioning context via B10/B14','Retain IV-based model band definition and source date; no calibrated chance inferred','Moves/GEX producers'),
('Probability/hedging-flow interpretation','Served Stability/Pin Target/hedging wording','BLOCKED_DATA','Qualified source score/context detail; raw evidence retained','No audited calibration or observed dealer flow; interpretation withheld pending method proof','Incumbent measurement producer / D09'),
('Computed source GEX/VEX/CEX metrics','gex_engine.py / GEX view','RETAIN','Existing supported metric controls and source method panel','Each family retains its actual computation and unit; no cross-family enablement','Incumbent producer; VEX precise-unit gate'),
('Uncomputed matrix Vanna/Charm','D08B handoff; source-specific availability','BLOCKED_DATA','B09 unavailable control with supported Gamma path','Unavailable stays unavailable; no simulated zero or upgrade promise','Relevant Greek producer'),
('Flow Surface field snapshots','SurfaceView; surface_dates','RETAIN','B10 Surface / Flow context','Strike × session-time field object remains distinct from Gamma/IV surfaces','Existing field/replay owner; D09 consult'),
('Field snapshot/candle interval distinction','SurfaceView temporal contract','RETAIN','Existing Surface controls; source annotation','Changing candle interval must not imply field resampling','Incumbent temporal source'),
('Positioning source bands and controls','PositioningView; p-U-0 boards','RETAIN','B14 Positioning workspace; B10','Keep GEX/moves primary and optional aggregate/matrix/quad/grades context','Incumbent positioning components'),
('Levels roles, voids and confluence','LevelsView levels.v1; p-U-0','RETAIN','B14 + existing full detail controls','Anchor/walls/flip/cluster/launchpad/counter/trapdoor and all cluster marks remain','Levels producer'),
('Level label collision handling','LevelsView','IMPROVE','B14','Labels can move; exact-price ticks and leaders stay anchored','Existing Levels geometry'),
('Null Levels regime','LevelsView nullable label ternary','IMPROVE','B14 Unknown','Correct proposed display; null must not be relabeled Slippery','Levels consumer; future build'),
('Levels palettes and source notes','LevelsView','RETAIN','B14 Blue/orange; Source convention','Retain accessible palette and selectable source notes','F02 / Levels consumer'),
('Expiry-led term structure','VolView; p-D-0 UM6-0','IMPROVE','B04/B08','Proportional tenor axis, selected expiry, real missing-point gap','vol.v1 producer'),
('Call/put smile and skew','VolView; p-D-0','IMPROVE','B04','Exact expiry/strike, separate nullable series, distinct shapes and selected guide','Volatility source method'),
('Missing selected expiry','p-D-0 XLX-0/XMP-0','IMPROVE','B08','Preserve selection and offer explicit alternatives, never nearest substitution','Vol source availability'),
('ATM IV, RV and published VRP','volTypes.ts/VolView','RETAIN','B04 reference context + existing history controls','Percent units; published VRP verbatim; horizons visible','Existing vol.v1 producer'),
('IV history/rank/coverage/since','VolView; volTypes.ts','RETAIN','B04 History and Rank windows','Keep 252/all windows, coverage and nullable history fields','Published history/rank source'),
('RR25 and rank method identity','gex_model.py / volTypes.ts','IMPROVE','Source & method; documented sign/window contracts','Opposite RR signs and different rank windows cannot share an unlabeled field','Macro/Terminal measurement owners'),
('Deep-ITM wing handling','volTypes.ts / VolView','RETAIN','Smile controls; explicit reversible trim','Do not present unreliable default wings as interpolated trustworthy observations','Existing vol consumer'),
('Fitted/model-qualified IV terrain','researchVolatility.ts fit:null; p-H-0 lineage','BLOCKED_DATA','Reported smile/term and exact rows remain usable','No fitted surface/model/availability is supplied','Volatility model/source owner'),
('Qualified Gamma 3D columns','ExposureSurface.tsx; R2 1IEM-0','IMPROVE','B05','Keep discrete data; add calibrated ticks/linear height reference/selection leader','Qualified projection model'),
('3D modes, windows, cap, elevation','exposureSurface.ts','RETAIN','B05 Net/Scope/Camera menus; B10','Net/gross/absolute; 2/4/8%; 5/9/15 expiries; 20/30/45/60 degrees','Existing Surface component'),
('Full-lens magnitude tiers','exposureSurface.ts','RETAIN','B05/B06 exact alternative + legend/method','Cropping does not recolor retained cells; preserve actual tier thresholds','Existing Surface model'),
('Source-session DTE and population change','exposureSurface.ts','RETAIN','B05 inspector/source and comparison','DTE anchors to book session; prior delta needs same population and finite values','Qualified source coordinator'),
('Equivalent accessible 2D','ExposureMap exact values; Lab table','IMPROVE','B06/B11/B13','Same full dataset/selection/filter/mode; all controls and zero/null reachable','Existing projection and table owners'),
('Published chain point cloud','ResearchScene/researchLabAdapter; p-H-0 18G0-0','RETAIN','B13','Mirrored side, ordinal expiry, hollow negative ΔOI, volume/OI/ΔOI; no fitted terrain','Research Lab existing adapters'),
('Lab filters/camera/three-item comparison','OptionsResearchLab','RETAIN','B13 controls and inspector; exact table path','Side/expiry filters, reset/front/top/orbit/zoom, arrow selection and compare cap','Existing admitted Lab'),
('Lab draw cap and full exact rows','ResearchScene/OptionsResearchLab','RETAIN','B13 + B11 interaction pattern','20,000 nonzero mark cap; 50-row pages retain every admitted row and zero/null','Existing Lab renderer/table'),
('Source coordinate versus instrument','researchLabAdapter; D08 node/pin','IMPROVE','B13/B17','root|expiry|side|strike is a coordinate; invalid/duplicate exclusions visible','Source resolver / D08C'),
('Lab IV session join','researchVolatility.ts','RETAIN','B13 Volatility for matching session','One percent→ratio conversion; same source session/coordinate; availability remains null','Existing vol adapter'),
('Unadmitted Lab replay/flow lenses','OptionsResearchLab unavailable evidence states','BLOCKED_DATA','Existing reasoned lens + source/return path','Missing chain-time/package evidence cannot become a working replay or flow model','Incumbent evidence and replay owners'),
('Durable options investigation save','AdmittedOptionsResearchLab; D08 saveIntent','BLOCKED_DATA','C/D23/native Investigation only after admission','Retain unavailable reason; no fabricated saved receipt or new persistence plane','D08C / D23 / existing Save owner'),
('Research identity/entitlement gate','AdmittedOptionsResearchLab','RETAIN','B15 access states; all Lab/2D entry points','2D alternative does not bypass source identity/access/distribution','Existing admission owner / D08D where scoped'),
('Phone navigation/KPI access','R2 phone 1HL2-0 clipping','IMPROVE','B02/B03/B10/B11/B17','Complete menus, visible qualifications, stacked KPIs, precise selection before tiny-cell tap','D08B + released F01/F02'),
('EN/ZH and light/dark','p-D-0 EN/ZH; p-H-0 light/tablet/phone','IMPROVE','B03/B06 ZH light; B01/B02/B05 dark; B04/B08/B14 light','Wrap long labels while preserving ISO identity, units and source meaning','F02 localization/theme contract'),
('Keyboard/touch/reduced motion','ExposureMap/Lab existing controls','IMPROVE','B06/B11/B12; actual browser acceptance owed','Visible focus, full exact path, 44px controls/48px rows, no forced orbit/hover/WebGL','F02 primitives / existing components'),
('Loading/empty/partial/stale/error/access','Existing readers and R2 recovery states','IMPROVE','B08/B09/B15','Reasoned states isolate optional failure, root-fence stale evidence, no false plan-required','Existing reader/access owners'),
('Exact return and no implicit save','D08 returnContext and existing history codecs','IMPROVE','B03/B07/B10/B17; interaction contract','Restore identity, filters, node, focus and scroll; named fallback only','D08 / C / D existing codecs'),
('TerraShade study lineage','p-T-0, nine incumbent boards','RETAIN','Unmodified reference lineage only','Do not revive the unapproved study as a new product or duplicate source owner','Existing Paper custody / D08')
]
items=[]
for i,r in enumerate(rows,1):
 cap,baseline,disposition,successor,reason,owner=r
 items.append(dict(id=f'R{i:02}',capability=cap,baseline=baseline,disposition=disposition,successor=successor,reason=reason,dependency_owner=owner,review_status='Candidate specification; formal RIG draft. See REVIEW for bounded independent findings.'))
counts=dict(collections.Counter(x['disposition'] for x in items));counts.setdefault('REMOVE',0)
(root/'CAPABILITY_LEDGER.json').write_text(json.dumps({'scope':'D08B exposure / volatility / 3D / positioning presentation','counts':counts,'items':items},ensure_ascii=False,indent=2))
md='# Capability retention ledger\n\nThis is a source-to-candidate contract, not a claim that new runtime paths have been implemented. Baselines are at the source pins in README; Paper references are in Terminal `01M3NSZGE8JWN2EZCSF0DT05RM`. Formal reference status remains RIG draft. The independent source audit supports the map; bounded product/taste findings and their limits are in REVIEW.\n\n'
md+='**Disposition counts:** '+', '.join(f'{k} {v}' for k,v in sorted(counts.items()))+f' — {len(items)} capabilities. No product capability is silently removed.\n\n'
md+='`BLOCKED_DATA` retains a useful visible source/unsupported state and a named owner. `RELOCATE` has an explicit reachable successor; it does not authorize a new owner or store. Advanced controls under menus remain acceptance obligations. Draft specifications of unsupported interpretations are not production removal decisions.\n\n'
md+='| ID | Capability / baseline | Disposition | Reachable successor | Rationale and dependency owner |\n| --- | --- | --- | --- | --- |\n'
for x in items:md+=f"| {x['id']} | {x['capability']} — {x['baseline']} | {x['disposition']} | {x['successor']} | {x['reason']} **Owner:** {x['dependency_owner']} |\n"
md+='\n## Boundary and review notes\n\nD08A scan/tape, C-owned Plan/payoff/saved scenarios, D-owned replay admission/cursor/distribution, other Options categories and global shell/registry ownership are not writable D08B scope. The ledger retains their transitions without duplicating their screens or authorities.\n\nPhone qualification, complete menu destinations and exact-value targets passed the independent static remediation review. Source audit and later full product/taste review remain advisory; they do not make every ledger row formally approved. Source-level retention must be verified again in the future implementation, especially closed-menu destinations, marginal graphics, source-specific calculations and keyboard/return behavior.\n'
(root/'CAPABILITY_LEDGER.md').write_text(md)
print(json.dumps({'count':len(items),'dispositions':counts}))
