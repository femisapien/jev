# Global bot audit and improvement priorities

11 October 2026. The strongest next direction is to optimize complete trips and recoverable
progress, while making the evaluation a better predictor of the live client. Faster attack
selection alone has a limited ceiling. The bot spends most of its time getting into position,
recovering, searching, servicing itself, or waiting. Several local failure rules still combine
into loops that the individual rules were intended to prevent.

The accepted full-bag repair is useful evidence that removing a small progress blocker can
help. It is not evidence that the overall architecture is optimal, that the custom speed score
is equivalent to elapsed leveling time, or that hive gains transfer exactly to Windows.

## Scope and evidence

The reference code is shared bot `35ba9fd` and JevHive `f1da2be`. At the start of this audit,
the hive played `35ba9fd`, the live checkout and remote main remained `8d39836`, and no candidate
trial was running. The three remaining queued candidates had closed with merge conflicts.

The review covers the perception and action boundary, supervisor and runtime, guides and
quest compilation, combat, navigation and transport, recovery and services, learned memories,
model coaching, simulator adapters, experiment scoring, recording, and deployment. It combines
targeted source inspection with full offline suites, compilation of all 52 race/class routes,
recorded failure inspection, small executable probes, and a sensitivity analysis of the latest
accepted trial. This is a system audit, not a claim that every line or every in-game situation
has been verified. The two repositories contain about 118,000 Python lines including tests.

The fresh time budget covers **05:00–08:00 BST on 11 October**: **2,893 overlapping runs,
227 characters, and 625 recorded bot-hours**. All 3,616 selected run summaries were present
and current; runs selected for boundary overlap need not contribute time inside the window.
This is an observational fleet snapshot, including the parity shard and both coaches, not a
new randomized comparison. Different classes and level mixes must not be ranked causally by
their pooled XP/hour. The separate 00:00–04:00 snapshot mixes trial arms and is diagnostic only.

[Compact evidence](2026-10-11-global-audit-evidence.json) accompanies this review. Full reports,
cached-run membership, source fingerprints, raw trial records, diagnostic rows, and replay
scripts are in `/home/ash/JevHive/var/audits/global-2026-10-11/`. No live game session was run.

## What current play costs

| Activity | Share of measured time | Implication |
|---|---:|---|
| Fighting | 20.9% | Rotation improvements affect a minority of the total journey |
| Approaching targets | 20.2% | Camp selection and approach safety deserve first-class planning |
| Idle and deliberate waits | 17.5% | Includes recovery waits and failures; it is not all removable |
| Resting | 11.4% | Optimize mana, food, location, and the next encounter together |
| Dead or a ghost | 8.7% | Prevention and recovery decisions have substantial downstream costs |
| Services | 7.3% | Bundle sales, repairs, purchases, and training into useful trips |
| Searching | 5.7% | Repeated empty camp visits need different destinations or information |
| Other travel | 5.2% | Measure complete journeys, including interactions and interruptions |
| Looting | 2.6% | Smaller current opportunity than routing and recovery |
| Session overhead and quest interaction | 0.4% | Very low hive interaction time is not a live UI benchmark |

The snapshot produced **2,184 XP/hour, 28.3 kills/hour, 3.60 deaths/hour, and 0.66 hand-ins/hour**.
Quest rewards supplied **14.5% of XP**; **68% of time** was on grind steps. At levels 16–20,
hand-ins fell to **0.21/hour**, with **4.07 deaths/hour** and **18% of kills giving no observed XP**.
These aggregate rates describe the current system; they do not establish a human-speed ratio.

More diagnostic observations:

- **43% of approach-operation time** ended with a combat-interruption result: 6,605 operations,
  averaging 30.4 seconds. Operation durations can nest and are not an additional exclusive
  time category. Some interruptions may be useful fights; avoid treating every one as waste.
- **83% of recorded deaths** occurred in defensive fights; **56%** involved two or more
  attackers. **38%** had broken equipment. These are associations, not proof that every such
  death would disappear with a repair or a route change.
- Decisions waiting for resurrection sickness accounted for approximately **10.5% of time**.
  Combined with dead/ghost time, recovery accounted for roughly **19.1%**. Decision attribution
  near window boundaries is apportioned from whole runs, so this is approximate.
- **11% of kills** had no observed XP: about 8.4% grey, 2.0% tagged by another player, and 0.6%
  otherwise unpaid. Some grey kills can still be necessary for quests or self-defense.
- Median successful fights took **15.5–21.1 seconds by class**, while mean measured kill cycles
  took **48.6–78.9 seconds**. Kill-cycle rates omit other activities and must not replace total
  played-time rates.

For scale, a hypothetical 25% reduction in fight time saves only about 5.2% of total time,
or **5.5% throughput**, if rewards and all other costs stay fixed. Halving approach plus travel
time would imply approximately **14.6% throughput** under the same assumptions. Neither is a
forecast; costs overlap across interventions, and these estimates must not be added.

## Findings requiring action

### P1 Supply failures can bypass both retry protections

`jev/coach/policy.py:934` permits a nearby provision purchase using `_barred`, bypassing
`can_restock` and its `no_supplier` note. `jev/run/supervisor.py:333` deliberately exempts
`no_supplier` and `too_far` from generic service backoff because the note should suppress
retries. Each rule is locally understandable; together they allow immediate repetition.

In run `20261011T051730-09cc38`, the level-10 draenei hunter recorded **1,763 aborted**
`BUY_AMMO_REAGENT_FOOD` attempts with “no generated supplier in the measured zone”, all under
`service.provisions`. Its observed zone was Bloodmyst while its coordinate frame was Azuremyst.
The run had 958 copper and four free bag slots. This is the same cross-zone provisioning
failure class previously diagnosed, still present in the accepted baseline.

An offline probe confirms that `can_restock` returns false after `no_supplier`, while
`services` still proposes `service.provisions`. Explicit generic service failure suppresses
the proposal, but the supervisor's exception prevents that failure from being recorded here.

**Repair design:** use one shared eligibility result for planning and execution, including
observed zone, actual merchant offers, and the purpose of the trip. Block an unchanged failed
request until relevant evidence changes. Keep a nearby purchase possible after an unrelated
long-distance `too_far` result; restoring a blanket half-hour ban would recreate the earlier
regression. Test re-entry after a zone, merchant, stock, or inventory change, and across session
boundaries. This is a higher-confidence next fix than another broad combat bundle.

### P1 A passed hive trial is not a demonstrated live improvement

Most farm shards still run with optional parity off. Shard 7 emulates several client
restrictions but explicitly has **quest parity disabled**. The current shared baseline does
not declare mandatory quest/flight parity. The rejected speed-transfer branch does, which
means its test changed both behavior and the observation contract.

Even all parity parts retain server movement, ID-based actions, complete server-backed window
information in several adapters, and timing sampled from prior live sessions. Padding action
durations does not reproduce correlated visual failures, facing errors, wrong-floor movement,
or missed UI inputs. `hive/body.py` also differs in exploration rates and limits ordinary
flights to night elves for the current baseline.

The newest directory in the inspected live run store is **29 September**. The saved calibration
report is dated **28 September** and includes large hive/live differences. It cannot validate
the current code. The code deployment path requires a shared suite, hive soak/guard, and an
offline Windows check; it does not require a fresh matched live performance result. Prior
promotion has a separate calibration mechanism, which is not equivalent to a code gate.

**Change:** define a versioned observation/action contract and test both arms under the same
contract. Keep a fast simulator tier, a constrained client-contract tier, and an actual-client
tier with distinct results. Later authorized live validation must cover quest assembly,
cross-zone supply purchases, interrupted approaches, recovery, flight interactions, and
indoor corners. “Same shared code” remains valuable, but it is not the transfer criterion.

### P1 The speed metric and experimental independence need strengthening

`hive/reward.py` divides normalized progress by **played time plus 120 seconds per death**.
Real death and recovery time is already in played time. This is an intentional preference for
reliability, not pure leveling speed. The normalization curve uses completed levels from the
current registry, including observations acquired after a historical trial began; it is not
frozen in the trial record. Slow unfinished levels do not enter that reference curve.

Treatment is assigned to farm processes, but intervals resample characters. Process sets are
chosen deterministically to balance counts, without explicit class/level/route balance.
All processes share `choices.json`, route memory, danger learning, and measured values.
Candidate lessons can therefore affect controls. Shared world spawns create another path
for interference. The current hive also has scaled respawn times on 4,587 creature spawns
and 2,727 object spawns, which must be part of the environment contract. This limits causal
attribution; it does not
justify declaring every result invalid or discarding a working fix.

The full-bag result survives several checks:

| Calculation | Adjusted index difference | 90% interval |
|---|---:|---|
| Recorded official trial | +0.0775 | +0.0043 to +0.1395 |
| Reconstructed with the current reference curve | +0.0752 | +0.0020 to +0.1420 |
| Curve frozen to levels known before the trial | +0.0830 | +0.0087 to +0.1353 |
| Frozen curve without the extra death penalty | +0.0996 | **−0.0150 to +0.1485** |

The reconstruction uses the recorded window, 78 candidate and 96 control speed observations,
and cached death records. Its slightly different normalization explains why it should not be
presented as an exact reproduction of the stored verdict. A diagnostic process-cluster
bootstrap with fixed adjustment also remained positive, **+0.0169 to +0.1101**. With only
three candidate and four control processes, that estimate is not a substitute for a better
assignment design. Leaving any one process out left the point estimate positive, but five
of seven intervals included zero; smaller samples naturally lose precision.

**Interpretation:** the official score gain and reduced deaths remain supported under the
existing rule. Pure elapsed-time improvement is promising but not yet established by this
diagnostic. These are sensitivity analyses, not a retrospective change to the acceptance rule.

**Change:** make time to specified level milestones, progress per actual played hour, completion
rate, and stalled-character tails primary. Keep the death-penalized score as a separately named
utility measure. Freeze the reference curve, route/data versions, and learned state at trial
start. Give each arm an isolated copy of learning state. Randomize and balance sufficiently
many independent character/environment units, or analyze the actual assignment clusters.
Predeclare target and decision window, test the evaluator on identical-code trials, and
replicate gains on fresh cohorts. Report unfinished characters, not just successful finishers.

The current judge closes ordinary sufficiently populated trials at the first eligible look;
this is not simply “keep peeking until significant”. Nevertheless repeated experiments,
data-dependent extensions, and any future interim stopping need an explicit error-control
policy. Time-uniform confidence sequences are one possible tool for genuinely sequential
evaluation, under their required assumptions ([Howard et al.](https://arxiv.org/abs/1810.08240)).

### P1 Deployment can accept an inconclusive stability result

`hive/guard.py:596` converts a sufficiently long, still-unresolved guard to `pass` with
`undecided=True` once the required cache reads are complete; `passed()` then authorizes
deployment. Tests explicitly preserve this behavior. This is an operational continuation
rule, not statistical proof of non-regression.
The canary's risk guards also use the **lower** confidence bound: they reject demonstrated
large harm rather than establish that harm is below the limit. The bag trial's stuck ratio
was 1.165 with interval 0.935–1.474 and passed the 1.25 guard.

**Change:** distinguish `improved`, `noninferior`, `inconclusive`, and `harmful`. An inconclusive
guard can permit continued hive observation without granting a claim of live readiness.
Require an immutable release record tying shared code, hive adapter, generated addon, routes,
catalogs, observations, and test outputs together. Introduce this prospectively, without
rewriting historical verdicts or changing the active rollout during an audit.

### P1 Correctness fixes are being bundled with performance experiments

The speed-transfer trial combined quest evidence repair, cross-zone provisioning, flight
selection, wider flight use, and stricter parity. Its lack of an aggregate speed win does not
establish that any individual correctness repair is unnecessary. The repeated provisioning
failure above remains a concrete defect. Requiring every repair of a rare observation bug to
move the entire fleet's XP rate can preserve known incorrect behavior indefinitely.

**Change:** separate correctness contracts from performance hypotheses. Prove quest-log
membership and provisioning agreement with captured-state and transition replays; run targeted
gameplay slices and broad non-regression checks. Trial flight selection and other optimization
choices separately, with identical sensing. Preserve the rejected branch for evidence rather
than automatically shipping or discarding its whole bundle.

### P2 Unknown observations can be treated as readiness

On current code, `Rest.until` returns `healthy` for a readable dictionary with no health gauge;
`until_both` returns `healthy` when health is full but mana is absent. The comparison builds a
list of positively low gauges, then calls an empty list healthy. Separately,
`Hunt._ready_to_pull()` returns true when its read is `None`, and permits absent health.
Downstream fight checks may still prevent action; these probes establish a local contract
failure, not a measured attribution of current deaths to missing gauges.

**Change:** distinguish ready, not ready, and unknown. Unknown should trigger a bounded fresh
read or explicit preemption, and never count as a successful recovery. Keep defensive action
possible on positive combat evidence. Add transition tests for missing gauges, stale frames,
death during rest, and delayed consumption acknowledgement.

### P1 Quest selection has a large capability and planning gap

All **52 route files** passed the current static readiness checks. They contain **5,017 quest
placements**, not unique quests. Compilation retains **3,370** before the worthless-quest
filter and **3,331** with production filtering, about **66.4%**. The earlier 3,370 figure used
the former definition; this audit did not discover a new 39-quest regression.

There are **726 prerequisite exclusions**, 139 event-interaction exclusions, 134 unplaced
destinations, 91 mixed-family counter-identity exclusions, 54 unverified counter mappings, and
49 missing interact executors. Some exclusions are intentional: elites, unrewarding errands,
and unsafe/unsupported quests must not be forced through. A static readiness pass proves
internal compatibility of the retained route, not that those quests complete in play.

**Change:** rank missing capabilities by the feasible quest chains and reward they unlock,
not by the number of supported node kinds. Build counter identity and item/interact contracts
before widening routes. Then compare a short-horizon scheduler of held quests, useful accepts,
hand-ins, and services against the sequential guide. Count actual completed trips and hand-ins.
The preserved `quests3` work is a starting point for review, not a validated release.

### P1 Encounter selection and logistics dominate much of combat loss

The current defense, equipment, and recovery associations argue for optimizing the cost of
the next several kills. Improving a successful fight's damage rate while walking into more
packs, going dry, or breaking equipment can lower total throughput. The fixed 1.9-second cast
guard has recorded client-rejection evidence behind it; removing it blindly is not a justified
optimization.

**Change:** estimate successful XP per complete encounter cycle, with explicit resource,
durability, aggro, and retreat constraints. Select a camp and safe approach together. Learn
accepted-action timing by class and observed acknowledgement before reducing delays. Test
single-target, adds, line-of-sight failures, low mana, pet/ammo loss, and broken-gear scenarios.
Report successful kills and all failed attempts; success-only fight durations are insufficient.

### P2 Transport and recovery need one cost model

Current transport is a set of walk, teleport, lift, hearth, and flight decisions. Boat/zeppelin
and mount names in the skill catalog do not give them executors in `LiveBody.HANDLERS`.
The retained routes include 546 Darkshore flight-dependent steps, 93 Thunder Bluff mesa steps,
43 Darnassus portal steps, and three Moonglade steps whose druid teleport is not cast.
These are repeated step placements, not distinct failed trips.

**Change:** use a transport graph with ground access, discovery, price, boarding/wait,
ride/loading, exit travel, risk, and failure recovery in a common unit of expected seconds.
Start with the supported modes and measured journeys. Add a new mode when it unlocks a
valuable route and can prove boarding and arrival. Reuse learned successful indoor paths as
bounded hints; keep the navmesh and observed-position checks as a fallback. Compare complete
door-to-door times, including failed journeys and recovery, not path length alone.

### P2 Learning and model coaching need their own proof of value

Choice sampling currently optimizes local payoff per second. Station keys encode objective
and position, while their lifetime counters do not expire by age. That can retain lessons
from other gear, classes, population densities, and code versions. A shared memory is useful
for training and throughput, but inappropriate as an unacknowledged channel between test arms.
Recorded XP on visited routes is also observational evidence, not the counterfactual value of
routes the policy avoided.

In the fresh snapshot the model-coached group had 2,015 XP/hour versus 2,367 for the local
rules, with 3.96 versus 3.26 deaths/hour. Level/route composition and shared learning make
this **insufficient to claim that the model causes worse play**. It is equally insufficient
to assume that more model involvement helps.

**Change:** retain a strong rules-only benchmark. Evaluate the coach's incremental benefit
with balanced assignments and separate memories. Log the offered alternatives, selected
action, selection probability where defined, freshness, and actual downstream cost. Condition
learned estimates on relevant context and version; use bounded forgetting or reset after
material changes. Deploy learning only in capabilities where it beats the simpler baseline.

### P2 Reproduction and experiment operations are incomplete

The inspected run manifest contains only run ID, store version, start time, and PID. It does
not pin code, route, addon, world/catalog, parity, or learned-state versions. Some information
exists in other logs, but a session cannot be reproduced from its manifest alone. The audit
saved hashes for 225 route, catalog, learning, and configuration files as a snapshot.

`Humaniser.for_client` seeds defaults with Python's process-dependent `hash(client_id)`.
An offline two-process probe produced different timing and stagger values under different
`PYTHONHASHSEED` settings. Its determinism comment is stronger than the implementation.
Use an explicit stable seed and record it; this is about repeatable tests.

The three closed queue entries are also substantive branches, not just trivial conflicts:
the learning branches contain thousands of added lines relative to their merge bases.
Blindly merging them would combine recovery, combat, and learning hypotheses and repeat the
attribution problem. Rebuild small candidates on the accepted baseline, preserve their
original targets, and link conflict closure to replacement or explicit retirement. The next
trial should not depend on someone noticing that an empty queue has stopped exploration.

## Alternative designs worth testing

The leading option is a **short-horizon trip planner with verified skills**. The guide supplies
opportunities and constraints rather than an instruction pointer that must do every next
step. At a safe decision boundary, the planner evaluates a small set of feasible sequences:
work two nearby held quests, sell and repair at the return hub, hand both in, then move to the
next region. It executes the first action and replans when observations or costs change.

Every action needs observed prerequisites, expected progress, resource costs, an expiry time,
and explicit reasons to retry or stop. Cost estimates must include travel interruptions,
service detours, recovery, and unproductive attempts. Expected reward must respect inventory,
quest dependencies, survival, and uncertainty. Start with a bounded beam over a few candidate
trips; a continent-wide optimal planner is not needed to test the hypothesis. Compare it with
the existing guide under identical inputs before giving it control.

| Alternative | Where it could win | How it must earn adoption |
|---|---|---|
| Carefully scripted fast routes | Known classes and starting areas; small complexity and predictable behavior | Beat the current guide on fixed starts and fresh held-out runs, including failures |
| Short-horizon trip planning | Quest bundling, service timing, camp choice, and transport | Lower whole-trip cost and milestone time without worse completion or death tails |
| Demonstration-trained local controllers | Visual targeting, doorway traversal, UI sequences, and recovery selection | Learn from recorded successful and corrected failures; beat existing skills on held-out scenes |
| Model-based encounter planning or bounded RL | Resource use, pull/retreat decisions, and class-specific rotations | Resettable fight scenarios with client-equivalent observations, then held-out realm/client checks |
| LLM-generated reusable skills | Rare unsupported quest interactions and debugging recurring failures | Offline proposals, deterministic verification, isolated gameplay checks, and rollback |

Imitation learning must handle states the learned controller itself visits, rather than only
copying ideal demonstrations. DAgger provides a research basis for iteratively collecting
expert corrections on such states; it is not evidence that a trained controller will beat
this bot without new demonstrations and evaluation ([Ross et al.](https://proceedings.mlr.press/v15/ross11a.html)).
Voyager demonstrates a reusable executable-skill approach in Minecraft. Its design supports
testing an offline skill-building role for a model here; its Minecraft results do not establish
WoW latency, visual-control reliability, or leveling speed ([Wang et al.](https://arxiv.org/abs/2305.16291)).

A broad rewrite or an LLM choosing every keypress would currently discard tested behavior
without resolving these measurement and observation gaps. Conversely, retaining all existing
rules indefinitely would preserve known loops. Replace responsibilities when a challenger
beats their current implementation, and remove the superseded path rather than stacking
another permanent exception on top.

## Concrete sequence and acceptance criteria

1. **Make the evidence reproducible.** Save a complete experiment manifest, frozen reference
   curve and arm-specific learning snapshots. Add raw-time and stalled-character outcomes.
   Separate an inconclusive release guard from a pass. Validate identical-code comparisons
   before relying on small percentage gains.
2. **Repair repeatable correctness failures separately.** Prioritize cross-zone supply
   agreement and the retry bypass, then quest-log evidence and unknown-readiness handling.
   Require captured-state replay, bounded retries on unchanged evidence, recovery after a
   relevant change, and a targeted gameplay confirmation. Retain aggregate non-regression
   checks; do not require every rare correctness fix to produce a fleet-wide speed win.
3. **Build the trip-planner challenger in shadow mode.** Use the same legal observations as
   the baseline. Record proposed trips, predicted cost, actual available alternatives, and
   prediction error. Shadow proposals can validate feasibility and runtime cost, but cannot
   prove the outcomes of unexecuted plans. Follow with a controlled gameplay trial.
4. **Attack the most costly encounter cycles.** Start with defensive engagements, broken
   equipment, dry casters, and high-level grind loops. Optimize entry conditions and recovery
   before reducing proven timing guards. Require per-class and level-band results.
5. **Expand valuable quest chains and transport modes.** Rank by reachable reward unlocked,
   observed completion probability, and expected saved trip time. Preserve source identities
   and dependency contracts; neither compile counts nor capability names count as completions.
6. **Qualify the actual live client when authorized.** Run matched manual and bot slices on
   the same realm, class, level, gear, money, route, rested-XP conditions, and crowd density.
   Keep client build and latency in the record. Extend to full milestone runs, retaining
   unfinished/stalled characters and operator interventions in the results.

The success contract should report **played time to levels 5, 10, 15, and 20; completion rate;
median and tail journey time; deaths and interventions per hour; no-progress time; and compute
or model cost**. A human comparison requires matched observations, not a guessed leveling-time
target. A better bot should improve the typical character and reduce the cases that need rescue.

## What should be preserved

The shared body/runtime, recorded operation boundaries, conservative quest exclusion,
generated world knowledge, cancellation and input-release ownership, navmesh interface,
rules fallback, and existing regression corpus are valuable foundations. The canary ancestry
repair and the full-bag regression are examples of precise, evidence-driven changes. The new
architecture should preserve these contracts and make them easier to inspect and replay.

## Validation and delivery

The full shared suite passed **3,267 tests**, with four navmesh cases initially skipped because
the isolated worktree lacked its built sidecar. All four subsequently passed using the existing
sidecar and extracted mmaps. The hive suite passed **390 tests**, with seven
skips for learned-line, pull-risk, and weapon-master capabilities absent from this baseline.
That is **3,661 passed tests and seven remaining skips** across the completed checks.
Validation results are recorded in the accompanying evidence file and the full suite XML/logs.
The audit branch contains review artifacts only. Production behavior, experiment rules,
stopped coordinator automation, and live input were not changed by this audit. The accepted
bag fix continues through the existing rollout process; the audit does not manufacture a new
performance verdict or restart the failed queue entries.
