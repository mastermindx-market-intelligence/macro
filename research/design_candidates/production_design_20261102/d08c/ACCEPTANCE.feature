@d08c @future_product @not_executed_against_product
Feature: Options research retains exact intent, evidence and effect knowledge
  A researcher can investigate, author, compare, save through the incumbent owner,
  and revisit a hypothetical Plan without implying a trade or losing uncertain custody.

  Background:
    Given the D08, F01, F02 and incumbent owner contracts are admitted for the test environment
    And the original held implementation carrier has satisfied its own release gates
    And the test uses an isolated authorized owner and synthetic source fixtures
    And no production write or uncertain production operation is used as a test fixture

  Rule: Exact source identity survives the journey
    Scenario: An aggregate exposure cell is context rather than a contract
      Given the selected D08B node aggregates multiple contracts
      When the researcher opens Research plan from that node
      Then the original node, lens and vintage remain the return context
      And no aggregate row becomes an option leg
      And the UI asks the researcher to choose unambiguous exact contracts

    Scenario: Adjusted roots are not normalized into ordinary roots
      Given source pins with roots "SPY" and "SPY1"
      When the researcher attempts to combine them in one Plan
      Then exact root identities remain unchanged
      And mixed-root admission is refused without deleting either source observation
      And ordinary SPY payoff eligibility is not inferred for SPY1

    Scenario: Source-list identity and contract identity remain distinct
      Given the same exact contract is pinned from DOI and Hot observations
      When the researcher compares the observations
      Then both original list/session/as-of bases remain inspectable
      When the researcher attempts to put both copies into one canonical Plan
      Then duplicate contract admission is refused

    Scenario: Repeating a pin does not refresh its observation
      Given an existing pin copied from source session A
      And the current list now contains source session B
      When the researcher selects the same pin again
      Then the original copied observation does not silently become session B
      And a deliberate current-evidence action can show B separately

    Scenario: Reported OI preserves basis and partial panel availability
      Given OI-by-strike is available and OI-by-expiry is missing
      When Structure opens
      Then the available panel retains its own report date and position session
      And the missing panel is named as unavailable rather than zero
      And no OI panel is labelled live or directional merely because it loaded

    Scenario: A late Structure response cannot overwrite another root
      Given a request for SPY is pending
      When the researcher commits QQQ as the root
      And the old SPY request returns last
      Then QQQ remains the selected root
      And no SPY panel is rendered as QQQ data

  Rule: Drafting preserves authored assumptions and independent research
    Scenario Outline: Leg quantity is a bounded whole contract count
      Given a valid exact contract pin
      When the researcher enters quantity <quantity>
      Then canonical admission is <result>
      And the entered text is not silently rounded or replaced
      Examples:
        | quantity | result   |
        | 1        | accepted |
        | 1000000  | accepted |
        | 0        | refused  |
        | -1       | refused  |
        | 1.5      | refused  |
        | 1000001  | refused  |

    Scenario: Zero entry and missing entry are different
      Given one leg has authored premium 0 and another has a blank premium
      When the draft is validated
      Then zero remains an explicit USD user assumption
      And blank remains null and incomplete
      And no observed mark is copied into the blank entry

    Scenario: Four independently authored legs survive edit and local transfer
      Given four unique same-root contracts with different sides, quantities and entries
      When the researcher edits one leg and applies to the local draft
      Then the other three identities and assumptions remain byte-equivalent
      And adding a fifth leg is refused with a visible limit
      And removing a leg is explicit and does not remove its original source evidence from other retained references

    Scenario: Research horizon is independent of option expiry
      Given all contracts expire on 2026-11-20
      When the researcher enters "Reassess by 10 Nov 2026" as the horizon
      Then that exact authored horizon survives Apply and reopen
      And the contract expiry is unchanged
      And no valuation-date or expiry field is silently derived from the research horizon

    Scenario: Incomplete or unsupported research remains useful
      Given a draft with mixed expiries and a retained thesis
      When the researcher requests an expiry payoff
      Then no curve is released
      And the mixed-expiry reason is visible
      And all legs, notes and source clocks remain editable and intact

    Scenario: Unsafe or oversized source graphs are refused before exposure
      Given a proposed draft with an accessor, cyclic object or over-limit source row
      When the canonical draft validator receives it
      Then admission is refused without invoking a getter or coercing source data
      And no Save or calculation request is sent

  Rule: Numerical output is qualified and has exact units
    Scenario: The independent two-leg fixture has signed producer semantics
      Given buy 1 SPY 600 Call at 5.20 and sell 1 SPY 610 Call at 2.00 USD per unit
      And both contracts have an explicitly stipulated multiplier 100 for this synthetic oracle
      When expiry intrinsic P/L is evaluated at spot 606
      Then signed cost is 320 USD and signed P/L is 280 USD
      And signed worst expiry P/L is -320 USD and best expiry P/L is 680 USD
      And the discrete break-even is 603.20
      And a displayed loss amount 320 retains the raw signed value -320

    Scenario: The fixed grid is not extended by an interactive hover
      Given strikes 600 and 610 in the current consumer
      When a request is prepared
      Then its spot grid has 103 points from 480 through 732
      And 600, 606 and 610 are members
      And 603.20 and 605 are not curve samples
      And a break-even annotation does not fabricate a P/L sample

    Scenario Outline: A malformed qualified response releases no partial math
      Given a valid prepared request and a response with <defect>
      When the response validator runs
      Then the whole numerical response is unavailable
      And no previous result is shown as current
      Examples:
        | defect                         |
        | reordered spot axis            |
        | altered spot axis              |
        | wrong expiry                   |
        | nonfinite P/L                  |
        | mismatched root coverage       |
        | missing reference digest       |
        | reference capture after known_by |

    Scenario: Terms cannot be inferred from an estimated premium
      Given a source pin has a null multiplier
      And a Hot premium estimate used a factor of 100
      When payoff admission is considered
      Then the pin's multiplier remains unknown
      And an exact qualified dated reference is still required
      And partial-leg calculation is not released

    Scenario: Current quote eligibility is never inferred from dated reference math
      Given an accepted dated hypothetical payoff response
      When source detail is opened
      Then current terms qualification and executable quote eligibility remain false
      And reference as-of, reference capture and calculation known_by are separately labelled
      And same-day expiry does not invent an expiry instant

    Scenario: An input edit fences a late calculation result
      Given calculation A is pending for input revision A
      When the researcher changes an entry price to input revision B
      And response A arrives
      Then the current result remains cleared for B
      And response A cannot overwrite B or appear as its calculation

    Scenario: Unbounded tails are not clipped into finite maxima
      Given a qualified short-call structure with unbounded high-price loss
      When the finite chart viewport is shown
      Then the loss remains UNBOUNDED
      And the right edge of the chart is not labelled maximum loss

    Scenario: A zero plateau is not described as never zero
      Given a mathematically offsetting structure with zero payoff over an interval
      And the returned discrete breakeven list is empty
      When break-even copy is rendered
      Then it does not assert that P/L can never equal zero

    Scenario: Missing costs do not produce a net result
      Given fees and slippage are not supplied
      When a gross expiry payoff is shown
      Then the result says before costs
      And net result after costs remains unavailable

  Rule: Comparisons disclose their basis
    Scenario: Observation-basis agreement is not economic equivalence
      Given two non-stale pins from one list and session but with different roots or expiries
      When the existing pin comparison is displayed
      Then any likeForLike flag is labelled same observation basis
      And exact contract differences remain visible
      And no best-trade ranking is produced

    Scenario: Entry alternatives retain per-leg inputs
      Given the baseline has buy 5.20 and sell 2.00 USD per unit
      When the researcher authors a higher-entry alternative with buy 5.40 and sell 2.00
      Then both leg-level assumptions are retained
      And total debit is 340, signed worst P/L -340, best P/L 660 and break-even 603.40
      And no aggregate net-debit field is submitted as a substitute for the legs
      And returning to baseline changes neither its inputs nor saved state

    Scenario: Different grids cannot be silently interpolated into an overlay
      Given two qualified plans produce different fixed spot grids
      When the researcher requests comparison
      Then evidence and individual results remain inspectable
      And the UI refuses a common numerical overlay or delta without an admitted identical axis

  Rule: The incumbent owner retains Save custody
    Scenario: Protected Plan admission is unavailable
      Given the protected manifest does not admit option_plan
      When the researcher views the draft
      Then account saving is unavailable with a reason
      And there is no substitute Save API, store or note-only fallback

    Scenario: Local admission is not Save
      Given the original owner has a fresh native New draft and a current owner guard
      When the validated Plan is transferred through its admission callback
      Then no network request, ID generation, storage, calculation or watch activation occurs
      And explicit Save remains a separate action

    Scenario: A stale admission callback cannot transfer to another context
      Given a Plan admission callback was acquired for owner A and native draft N
      When the owner, selection or fresh-draft context changes
      And the old callback is invoked
      Then it refuses without transferring data or sending a request

    Scenario: Journal retention failure prevents transmission
      Given session retention is unavailable or verified readback differs
      When explicit Save is requested
      Then zero Save requests are sent
      And the editable intent remains visible with an accurate local-retention warning

    Scenario: A lost response after commit never causes a duplicate
      Given the test owner commits the one submitted Save and drops its response
      When the client sees a timeout
      Then Save outcome is unknown and the original command remains retained
      And no second Save POST occurs
      When the original operation is reconciled through its owner
      Then the exact committed ID and revision are recovered without another effect

    Scenario Outline: An inconclusive operation lookup does not settle Save
      Given an unresolved original command
      When its operation lookup returns <result>
      Then the original command remains uncertain
      And another Save remains unavailable
      Examples:
        | result             |
        | not_found          |
        | 401                |
        | timeout            |
        | malformed response |

    Scenario: Known commitment survives unavailable readback and access loss
      Given an exact matching committed receipt has been received
      When the exact revision read fails or access expires
      Then the UI says research saved with reopen/access unavailable
      And it does not downgrade Save to unknown
      And it offers read/access recovery rather than Save again

    Scenario: Owner A to B to A preserves privacy and original uncertainty
      Given owner A has an unresolved Save
      When the session changes to owner B
      Then B sees no A Plan, admission, receipt or copyable draft
      And A's unresolved custody is not deleted or transferred
      When the session returns to A
      Then recovery uses A's original operation identity

    Scenario: Exact revision mismatch does not fall back to latest
      Given revision N of record R was requested
      When the reader returns N+1 or a different record ID
      Then the requested Plan is withheld with a mismatch reason
      And no different revision is silently substituted

    Scenario: Legacy locally rejected commands require original-owner recheck
      Given a retained legacy invalid_payload rejection without proof of non-application
      When recovery opens under the held helper contract
      Then the command is uncertain and the full original request goes to owner recheck
      And no automatic resend or insufficient result-only settlement occurs

    Scenario: Scenario capture conflict is explicit
      Given the native draft contains a scenario_capture incompatible with Plan-v3 admission
      When a Plan is attached
      Then the conflict is visible
      And neither scenario_capture nor Plan data is silently discarded or converted
      And no request is sent

    Scenario: Copy research draft is a local escape rather than a Save receipt
      Given the current owner has a readable local draft and account Save is unavailable or unknown
      When the researcher explicitly copies the research draft
      Then the readable exact identities, assumptions and source references are copied
      And credentials and protected transport data are excluded
      And no Save, new operation ID or watch request occurs
      And the original Save status is unchanged
      And clipboard failure is shown without claiming a successful copy

  Rule: Watch and revisit keep independent facts
    Scenario: Save succeeds while watch activation is uncertain
      Given research revision N is verified
      When an explicit watch activation response is lost
      Then research remains saved and watch outcome is unknown
      And neither another Save nor duplicate activation occurs

    Scenario: Unsupported watch conditions produce no alert request
      Given the researcher selects an exact strike, exposure change, rotation or event-time condition not implemented by the builder
      When watch setup is reviewed
      Then the unsupported condition is explained
      And no alert POST or new evaluator is created

    Scenario: A confirmed watch identifies the exact monitored research
      Given a watch owner confirms an active strict price threshold
      When success is shown
      Then root, comparator, threshold, unit, expiry, linked research revision and last evaluation are inspectable
      And the UI does not call a strict threshold evaluation a crossing event

    Scenario: Firing can be known while notification delivery is unknown
      Given an owner-confirmed firing with an original condition and source time
      When notification receipt retrieval is unavailable
      Then the firing and source time remain visible
      And delivery is unconfirmed rather than delivered or not-delivered
      And no firing or event ID is invented

    Scenario: Revisit compares observations with observations
      Given a saved Plan has authored entries but lacks original observed marks
      And new observed marks are available
      When Revisit opens
      Then the original mark cells say not retained
      And new marks are not aligned as a price change from authored entry
      And authored entries appear in a separate unchanged assumptions section

    Scenario: Revisit preserves per-firing history and correction custody
      Given one linked alert has two firings with different observed values and source vintages
      And its latest trigger stamp describes only the second firing
      And a third supplied receipt corrects the first firing
      When the researcher opens the existing firing-history detail
      Then each supplied receipt shows its own observed value and source vintage
      And the older firing never borrows the latest trigger value or note
      And the correcting receipt follows the original without replacing it
      And a capped readable queue with no row for a firing shows receipt absent rather than not delivered
      And an unavailable queue read shows delivery unconfirmed without inventing a receipt ID

    Scenario: Reassessment creates an explicit new revision
      Given exact saved revision N and separately fetched current evidence
      When the researcher assesses N as inconclusive and saves through the native owner
      Then a new immutable revision records that assessment and its relation to N
      And original evidence remains unchanged
      And no watch rearm or holding change occurs

  Rule: The complete task is responsive and accessible
    Scenario Outline: Primary tasks survive the real shell width
      Given viewport <width> with the actual F01 navigation and gutters
      When the researcher opens Plan, Compare, an editor and Revisit
      Then the useful content width is <content>
      And one overlay is active at most
      And exact contracts, research details, model limits and primary actions remain reachable
      And necessary two-dimensional scrolling stays within a labelled component
      Examples:
        | width | content |
        | 320   | 288     |
        | 390   | 358     |
        | 768   | 728     |
        | 1024  | 788     |
        | 1280  | 1008    |
        | 1440  | 1168    |
        | 1600  | 1328    |

    Scenario: Keyboard and focus survive close and a vanished origin
      Given the editor was opened from a selected row
      When it is closed using Escape or Cancel
      Then focus returns to that trigger if it still exists
      And otherwise moves to the named safe parent heading
      And saved data is not changed by closing or navigation

    Scenario: Theme, locale, zoom and motion do not change meaning
      Given long English and Chinese text, dark and light themes, 400 percent zoom and reduced motion
      When the complete research task is exercised with keyboard and screen reader
      Then signs, units, exact identities and source dates retain the same meaning
      And content reflows without whole-page horizontal overflow
      And errors are not color-only and charts have an equivalent values-table path
      And important mobile controls meet the 44px house target

    Scenario: The held implementation cannot be mistaken for a shipped feature
      Given only this design package and fixture verification exist
      When the return is reported
      Then RIG approval, product implementation, merge, deployment and production acceptance are not claimed
      And the next actions name the existing owners and their exact evidence gates
