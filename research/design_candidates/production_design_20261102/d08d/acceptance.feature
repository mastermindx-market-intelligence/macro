@D08D @proposed @not_executed
Feature: Historical replay preserves evidence and exact research context
  These scenarios are a specification for the incumbent Terminal test owners.
  No step definitions or product implementation are supplied by this design packet.

  Scenario: Originating Options selection survives the complete futures journey
    Given an admitted Options origin with exact instrument, view, filters, row, source cohort, scroll and focus
    And a qualified futures publication for the requested instrument
    When the researcher opens replay, chooses a published observation, opens evidence and returns
    Then the original owner restores every qualified origin field
    And no plan, alert or evidence record is created by navigation

  Scenario: Requested cutoff is not an observed timestamp
    Given published futures cutoffs at 13:45:00 UTC and 13:46:00 UTC
    When the admitted request asks for 13:45:30 UTC
    Then the existing reader selects 13:45:00 UTC
    And the view labels requested and selected times separately
    And no observation after the requested cutoff affects the view

  Scenario: Native IEX sequence fences a late old-timestamp trade break
    Given an admitted IEX artifact with an earlier selected native sequence
    And a later native break whose event timestamp is older than the selected market timestamp
    When evidence is computed for the earlier selected observation
    Then the later sequence is excluded before incumbent correction accounting
    And the earlier selected profile is unchanged

  Scenario: Same millisecond does not collapse two IEX observations
    Given two admitted IEX samples with distinct nanosecond instants in the same displayed millisecond
    When the researcher selects each retained sample
    Then the artifact position and original native fields remain distinct
    And displayed date formatting is never used as the identity key

  Scenario: A refresh cannot silently rebind an old artifact position
    Given evidence open on a sample in a verified artifact
    When refresh returns a different artifact with a different sample array
    Then the inspected identity is preserved or exact reconstruction is declared unavailable
    And opening the new publication requires an explicit action

  Scenario: An unavailable book is withheld rather than shown as zero
    Given an IEX sample with unavailable status and structural zero totals
    When the researcher selects the sample
    Then book totals display unavailable values and a gap reason
    And no zero-liquidity or interpolated-book claim appears
    And separately qualified captured executions keep their own scope

  Scenario: Time-only entry cannot claim exact IEX restoration
    Given the originating chart supplies an historical instant but no exact IEX artifact and native position
    When the replay reader has no qualified initial-selection resolver
    Then the original requested instant remains visible
    And any latest-retained default is explicitly labeled as a different selection
    And the researcher can choose a retained native observation without a new archive retrieval API

  Scenario: Open evidence follows the same committed observation as every analytical surface
    Given the chart, totals and open evidence show observation A in artifact X
    When the researcher previews and then commits observation B in artifact X
    Then preview leaves the committed analytical surfaces on A
    And commit changes the heading, chart, totals and inspector together to B
    When refresh reads a different artifact Y
    Then the entire X view remains coherent pending explicit transition
    And no old array position is silently rebound to Y

  Scenario: Direct observation choice reaches outside the drawn prefix
    Given the reader has 480 retained samples and the chart shows its final selected prefix
    When the researcher opens Choose observation and commits sample 7
    Then exact artifact position 7 and its copied native fields identify every displayed surface
    And an equal-timestamp sample at another position remains distinct

  Scenario: Account change clears an in-flight protected response
    Given a replay read started under account A
    When the current owner changes to account B before the response arrives
    Then the old response cannot paint data in account B's view
    And the current access result controls the visible state

  Scenario: Generic refusal cannot become a plan upsell
    Given a futures response with only access_required
    When the page renders the access state
    Then it says that replay access could not be confirmed
    And it does not infer a guest or plan-required result

  Scenario: A disappeared origin row yields an honest fallback
    Given a validated origin whose selected row or cohort no longer exists
    When the researcher returns from replay evidence
    Then the owner declines exact restoration
    And opens the named validated fallback with an explanation

  Scenario: Narrow evidence does not squeeze the chart
    Given a 1024 CSS-pixel viewport with the shared 196-pixel expanded navigation and 20-pixel gutters
    When the researcher opens evidence
    Then a 440-pixel modal is used
    And the domain does not automatically compact navigation or dock a 320-pixel inspector

  Scenario: Weekly positioning is outside historical evidence
    Given the futures cursor is historical
    When weekly CFTC positioning is expanded
    Then its report and retrieval clocks are displayed separately
    And replayEligible remains false
    And those values are excluded from evidence-at-cursor

  Scenario: Development harness remains excluded
    Given the production environment
    When /dev/options-plan is requested
    Then the route returns its existing not-found behavior
    And no customer navigation or route-admission change exposes it

  Scenario: An uncertain future save is reconciled by its existing owner
    Given a separately admitted D23 evidence save was submitted with an operation identity
    When the response outcome is unknown
    Then the UI shows uncertainty and reconciles the original operation
    And it does not submit a new operation or use another save owner
