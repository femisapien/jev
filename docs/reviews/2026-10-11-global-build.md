# Global overhaul implementation — 11 October 2026

The audit's implementation is on `build-global-20261011`. The shared runtime and the hive
adapter have separate commits. The hive patch is exported beside this document because
that repository has no remote. This is a candidate for measured qualification, not evidence
that leveling is already faster or comparable to a human.

| Audit finding | Implementation | Validation / limit |
|---|---|---|
| Supply retry loops | Persist the failed request and its evidence; nearby restocking respects unavailable suppliers; use both the guide and observed zone's merchants | Repeated unchanged requests stay suppressed; changed relevant facts allow another attempt |
| Rolling quest log | Preserve assembly while interacting; invalidate on painted membership changes; verify an already-held accept | Slow-reader and membership regression cases |
| Unread readiness | Unknown, nonfinite, or invalid required health/mana refuses a fresh pull or successful meal | Combat still permits defensive handling; a failed drink must produce a fresh usable reading |
| Hive/live mismatch | Both trial arms use the same painted observation contract and exploration settings | Simulator evidence remains labeled simulator evidence |
| Confounded experiments | Freeze routes, initial memories, reference curve, cohort, process assignment, adapter and world identity; isolate both global and character learning by arm | One protocol-2 comparison at a time; changed control code closes the comparison; a rebuilt candidate gets a new manifest |
| Biased speed score | Actual played time is primary; the previous death-penalized utility remains visible; bootstrap process clusters and refit adjustment inside resampling | Small cluster counts or rare-event evidence remain inconclusive; shared-realm interference remains a limitation |
| Survivors-only reporting | Report assigned-but-unobserved characters and right-censored next-level endpoints | Completion-only milestone averages are not speed claims |
| Inconclusive releases | Inconclusive guard results cannot authorize promotion; release records bind clean code, suites, trial verdict and matched client scenarios | Promotion requires measured evidence; elapsed time alone cannot pass the gate |
| Quest capability gaps | Recorded dialogue contract, explicit counter identity for mixed objectives, positive completion checks, dependency unlock ranking | Existing excluded routes are not silently certified; individual dialogue contracts still need real recordings |
| Local greedy work | Bounded trip planner with prerequisites, quest-log space, bag slots, money, risk, complete quest chains and service opportunities | Default is shadow; active execution revalidates its first action against the normal tracker/verifier |
| Combat/learning costs | Context-qualified, age-weighted choice records; objective estimates can include measured full-cycle cost and risk; first-action outcome and full encounter-cycle reporting | Last-update aging is a conservative view over additive records; model probabilities are explicitly unknown |
| Transport | Compare planned access and exit legs for known flights, broaden beyond race-specific restrictions, retain failure cooldowns, and share a seconds-based journey cost model | Flight durations remain estimates; boats/teleports require verified executors and observations before becoming usable edges |
| Alternatives | Pinned per-arm trip and coach settings; measured paired-episode comparison; rules/model and shadow/active experiment templates | Saved-state agreement is not a causal speed estimate; human reference episodes have to be collected |

The search budget is 24 opportunities, a beam of 16, and depth four. In 30 synthetic runs
with 1,000 input opportunities, median planner CPU time was **3.72 ms**, p95 **5.64 ms**,
and maximum **12.88 ms** on this host. This excludes sensing, navigation and model latency.
See [the machine-readable report](2026-10-11-build-validation.json). The 52-route capacity
report identifies recorded events and counter identity as the highest-value remaining
content work; its hypothetical unlock totals overlap and must not be added together.

## Validation

- Shared runtime: **3,321 passed**, zero failures or skips, 198 seconds.
- Hive adapter: **350 passed, 59 skipped**, zero failures, 85 seconds. Skips need external
  integration services or optional environments; they are not live-client validation.
- Shell syntax and whitespace checks pass.
- New regression coverage includes isolation, frozen inputs, changed assignments, fixed
  windows, rare-event uncertainty, censored milestones, readiness, quest membership,
  dialogue completion, planner resource constraints, and immutable release evidence.

The full suites ran in isolated worktrees against the local data and navigation assets.
No simulator process or rollout switch was changed during implementation. The user then
explicitly authorized a live mage test while away for seven to eight hours. That test must
record its own exact candidate identity and remain distinct from a completed release.

## Use and qualification

`--trip-mode shadow` records proposals and matched first-action outcomes in `trips.jsonl`.
`--trip-mode active` enables the challenger only after ordinary recovery/service priorities
and execution eligibility checks. `off` retains the existing guide policy.

Read-only tools:

```bash
.venv/bin/python tools/quest_capabilities.py PATH_TO_GRAPH.json
.venv/bin/python tools/encounter_cycles.py PATH_TO_RUN
.venv/bin/python tools/compare_episodes.py SAMPLES.json --output RESULT.json
```

A sample contains one independent assignment unit and candidate/control observations with
positive elapsed seconds, boolean success and a death count. Repeated units are rejected.
Model calls and human demonstrations can use the same measured endpoint format. This does
not estimate the result of an unexecuted alternative action.

The hive's `set --arm-settings FILE` and queue `arm_settings` field pin each arm's `trip_mode`
and `coach` (`rules`, `model`, or existing `roster`). The checked-in experiment templates
keep these comparisons separate. A requested model arm with no coach fails explicitly.
The fixed window begins only after all processes have adopted their assigned contract.

For release evidence, `tools/qualification.py suite --output PATH.json` runs the suite on a
clean committed checkout and binds its JUnit report to that commit. `assemble` takes these
suite records, a protocol-2 verdict, and `--client-result SCENARIO=RESULT.json` inputs.
`tools/release_gate.py` rechecks them before deployment. A candidate optimization must show
improvement; correctness-only changes can qualify through noninferiority.

The client scenarios are quest log, cross-zone supplies, interrupted approach, recovery,
flight and indoor navigation. Each needs at least eight independent matched units. Each
sample binds a run manifest, an episode summary, and its full trace by SHA-256. The summary
records scenario/unit, start/end times, observed completion and deaths, and matched realm,
client build, class, level, gear, route, rested XP, money, latency band and crowding band.
The gate recomputes elapsed-time bounds and rejects worse deaths, incomplete outcomes,
reused runs, stale evidence and unmatched conditions. A single mage's exploratory soak
cannot establish all of this by itself.

The release gate has no exemption that converts a missing live comparison into a pass.
An authorized candidate test runs the candidate before promotion and produces evidence;
a final release remains a separate decision based on that evidence.

For the authorized mage test, `tools/live_soak.py` holds the existing live-loop lock,
pins the committed candidate and launch configuration, and runs bounded native Windows
sessions for up to eight hours (six by default). It requires the expected character key
and shadow trip mode. Wrong-character observations, unread telemetry, repeated failures,
no XP/quest progress, excessive deaths, operator stop files, and the deadline stop the
test. Its six focused regression tests pass. Status is written to `var/live-test/status.json`,
with per-session logs in `captures` and full evidence in `runs`. This supervision does
not replace the release comparisons above or establish an improvement by itself.

The initial native Windows test exposed a WSL data-symlink deployment gap and a Git
identity issue with linked worktrees and detached stdin. The candidate now has readable
local data, and revision capture uses the owning WSL distribution with an explicitly
closed input pipe. The monitor also verifies the client's recorded revision. A live
review found that the teaching wrapper omitted the new trip callbacks; these now forward
to its live body, covered by a painted-radio integration test. Early play repaired broken
equipment, sold 27 stacks, and recorded a kill and XP gain. These observations confirm
execution, not a measured speed improvement.
