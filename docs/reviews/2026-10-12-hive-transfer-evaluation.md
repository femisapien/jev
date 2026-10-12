# Evaluation of hive benefit to the live bot

12 October 2026. **The hive has useful testing value, but the current setup is not delivering its intended role of making the live vision and click bot improve substantially faster.** It has produced shared-code changes, including fixes present in the mage. It has not demonstrated a corresponding gain in reliable live play. Continuing the same broad background farming is a poor default use of effort until the feedback path and actual client controller are addressed.

The evidence supports changing the hive's role, rather than discarding every component. Keep it for targeted tests of shared decisions, quest state, resource handling and combat rules. Make failures recorded in the actual Windows client the starting point for development, and require successful live execution before calling a change an improvement.

This assessment covers the live recordings, simulator adapters, memory publishing, calibration inputs, learning mechanisms, candidate ledger, latest fixed comparison and current resource use. It does not estimate an exact financial return or human-speed ratio: engineering time and a matched human benchmark have not been recorded. [Machine-readable evidence](2026-10-12-hive-transfer-evidence.json) accompanies the assessment.

## What happened to the mage

The latest two sessions, beginning at 00:41 BST, contain 30.35 minutes of observed play on the same tested commit. The controller requested a stop for thirty minutes without observed XP or quest progress; the final snapshot was dead, at level 17 and 0.79% XP. The small XP change appears near the end of the recording.

| Measure | Latest live result |
| --- | --- |
| Progress | Approximately 129 XP, inferred from the painted and quantized XP fraction |
| Quest hand-ins | 0 |
| Recorded kills | 21; the trace classifier places all 21 against grey targets at least six levels below the mage |
| Deaths | 1, at the end; subsequent recovery time is therefore absent from this window |
| Travel | 35.0% of observed time |
| Services | 31.7%, mainly class training |
| Fighting | 17.4%, classified as defensive encounters |
| Useful service completed | Two spells trained and placed on the action bar |

The approximate XP rate is 255/hour. The XP change is not matched to one of the 21 recorded kills, so those kills and the small final XP gain must not be presented as equivalent measures. Defensive kills can be necessary; their frequency here shows the cost of the journey, not necessarily a deliberate choice to farm grey mobs.

The logs show repeated approaches to Zaldimar Wefhellt, wrong-floor recovery, a route taking hundreds of turns, and failed indoor exits. The new movement guard did fire during an indoor stall. It bounded a particular failure; it did not make the complete journey reliable. Saying the mage was moving and fighting after restart was accurate at that moment, but insufficient evidence of recovery of the intended task.

The wider current-checkout sample contains 20 recorded sessions across several revisions: about 3.97 hours, approximately 11,409 XP, 102 recorded kills, ten deaths and no quest hand-ins. This includes real progress to level 17. It is neither a matched comparison nor evidence that the hive caused that progress. [Detailed latest-session analysis](/home/ash/JevHive/var/audits/hive-transfer-20261012/latest_live.txt) and [wider analysis](/home/ash/JevHive/var/audits/hive-transfer-20261012/all_candidate_live.txt) retain the time accounting.

## The hive bypasses the failing parts of the live client

| Capability | What the hive exercises | What remains unproven in the live client |
| --- | --- | --- |
| Guide, quest and service decisions | Much of the shared runtime and supervisor | Whether the chosen complete task can be executed promptly with the real UI |
| Combat choices | Shared fight logic with server-backed targeting and actions | Reliable visual acquisition, facing, range control and recovery from missed inputs |
| Navigation | Shared route planning followed by a separate server movement implementation | The actual keyboard follower, camera, water exits, doors, stairs and wrong-floor recovery |
| Interaction and looting | NPC/object identification and server-backed window/actions | Finding and clicking the correct screen target and verifying the resulting UI |
| Perception | Synthetic painted state, with optional restrictions and sampled delays | Screenshot capture, actual visual ambiguity, occlusion and correlated perception failures |
| Camera and focus | Successful camera methods and always-true focus | Keeping a real window usable throughout a session |

These differences are executable behavior, not just documentation. [ServerHid.click](/home/ash/JevHive/hive/client.py:300) refuses pixel clicks. [ServerTargeting](/home/ash/JevHive/hive/skills.py:173) faces targets by their server identifier. [ServerCamera](/home/ash/JevHive/hive/skills.py:1004) returns success without operating a camera. [ServerTravel](/home/ash/JevHive/hive/client.py:324) is a separate class that sends movement destinations to the server, with a direct-move fallback subject to a cliff check.

The latest live route guard is in [Travel](/home/ash/ForeverV2-global-build/jev/clients/travel.py:109). The hive neither inherits that follower nor executes its route-progress guard. Its overnight candidate comparison consequently cannot directly qualify that repair.

The fixed six-hour comparison did give both arms all observation-parity switches. That is an improvement in experimental fairness. Those switches still leave the server action adapters in place. After the trial ended, normal farming returned to its existing configuration: optional parity on shard 7, with quest parity disabled, and off on the other shards. Results from that broad background population should not be treated as an actual-client benchmark.

Adding a sampled delay to an exact server action can approximate elapsed time. It cannot reproduce a camera that remains wrongly oriented, repeatedly missing the same corpse, or a controller repeatedly selecting the wrong floor. Improving the simulator further may be useful for a specific shared decision, but recreating all of those failures is a much larger task than testing the real controller directly.

## Fresh hive lessons are not reaching the current mage setup

The code supports several distinct feedback paths. They must be assessed separately.

**Published memories are disconnected from the active checkout.** The mage loads priors from `ForeverV2-global-build/var/prior`, which does not exist. A read-only probe of the actual loaders returned zero prior choice groups, zero prior danger cells and no value table. Publishing instead targets `ForeverV2/var/prior`. The mage still has its own local learning records, and shared source changes, so this is not a claim that it has no learning at all. [Live loaders](/home/ash/ForeverV2-global-build/jev/run/cli.py:557) and [publisher](/home/ash/JevHive/hive/promote.py:237) establish the paths.

**Publishing is paused as well.** `PROMOTE_STOP` has existed since 8 October. The last installed prior at the old destination is from 8 October, containing 4,843 station options and 69,007 danger cells. Copying it blindly into the new checkout would not establish benefit. Its own calibration record passed only 5 of 14 overlapping creature-yield comparisons and 16 of 28 step death-rate comparisons; its overall danger-agreement field is false. Current publishing code reports that disagreement but does not require agreement before export. These historical, observational checks do not by themselves prove that every prior entry is harmful.

**Calibration is reading the wrong live recordings.** Both [calibrate](/home/ash/JevHive/hive/calibrate.py:33) and [senses](/home/ash/JevHive/hive/senses.py:28) still read `ForeverV2/runs`. Its newest run is from 29 September. Last night's recordings live in `ForeverV2-global-build/runs`. A recently refreshed timing file can therefore still be derived from old sessions. The feedback used to make the hive resemble the current mage is stale at its source.

**Some sophisticated learned tables are only connected to the hive.** [Hive session setup](/home/ash/JevHive/hive/run.py:248) loads pull-risk data for targeting/navigation and supplies learned rib yields to its runtime. The current live CLI does not wire those same tables into the corresponding runtime. Shared reader code existing in the repository is not evidence that the live bot uses it.

**Code changes do transfer, but raw bot-hours do not train the mouse controller.** The hive uses outcome tables, local choice learning, comparisons and programmer-made source changes. The inspected pipeline does not train a visual policy from its server actions. The hosted decision model remains `jev-1.13.0` in all 678 recorded calls in the current checkout. Successful inference calls are not model training. The latest two live sessions record routine/reflex execution, with no recorded visual teacher intervention. The source-diagnosis coach is separately quota-limited, and the coordinator's automatic cycles are held.

The new trip planner was also in shadow mode in all 60 recorded proposals in this checkout. Those records support analysis of proposed choices; they do not show that the new planner improved executed trips. That was a deliberate experimental setting, but it limits claims about benefits from the newest additions.

## The hive has produced useful results

The historical ledger contains 20 judged candidate entries: five kept and fifteen not kept. All five kept revisions are ancestors of the current live code. The retained work includes quest-spawn query batching, combat retreat behavior and bounded full-bag gathering retries. This is evidence that the hive has contributed shared-code changes and screened hypotheses, rather than producing nothing useful.

Those ledger outcomes are simulator judgments. They are not five independently measured live speed wins. Earlier comparisons also had weaker isolation and uncertainty handling, as documented in the previous audit. Rejecting a change can save debugging effort, but its value depends on whether the measured failure is relevant to the live client.

The replacement six-hour comparison covered 208 scored characters and about 1,213 character-hours. Its adjusted speed-index difference was +0.060, with a 90% process-cluster interval of +0.033 to +0.119. Its baseline-adjusted death-rate ratio was 1.116, with interval 1.014 to 1.267. The overall verdict was **inconclusive**, and nothing was promoted. There were only three candidate and five control process clusters, sharing a realm; 208 characters are not 208 independent assignments.

There is also a reporting defect in the percentage wording. Protocol 2 derives its speed floor from 5% of baseline, while [the description formatter](/home/ash/JevHive/hive/canary.py:1934) reconstructs baseline using the older 20% constant. Consequently the stored text says approximately 29% of baseline when the corresponding calculation is **7.34%**. The raw median index difference gives a separate 7.85% ratio; neither is a measured live speedup. The stored absolute interval and inconclusive gate remain unchanged. [Original verdict](/home/ash/JevHive/var/trials/1791762030529-71ff145652a2/verdict.json).

The new isolation, frozen inputs and refusal to promote an inconclusive result are worthwhile. They make a narrower claim more trustworthy. They do not turn server movement into a test of real clicks.

## The cost and the decision

At the audit snapshot, the hive's systemd group charged approximately 11 GiB of memory, including its server, farms, jobs and file cache; the working-set estimate was about 10.6 GiB. Its cgroup retains historical memory-pressure and OOM-kill counters, but those cumulative counters do not prove that resource contention caused last night's mage failures. Current pressure averages were zero. The architecture does consume substantial shared-host resources and creates maintenance work independent of fixing the live controller.

The recorded decision-model charge was roughly $0.29 for the day at inspection. That is not a total project cost: it excludes the development/diagnosis provider, machine costs and engineering attention. Those unmeasured costs prevent an exact return calculation.

**Decision: retain the hive as a supporting test system; stop treating broad unattended farming as the primary engine of live improvement.** Hundreds of characters increase the number of simulated situations observed. They do not shorten the diagnosis-to-fix loop for a stairway failure that the simulator bypasses. Present evidence does not justify expanding this workload.

## A development loop that addresses the live failures

1. **Connect and identify the real inputs.** Give the deployment one authoritative live-recording location and one versioned learning package. Record the files actually loaded in each session manifest. Align calibration with the active recordings. Keep source-specific memories separate and test prior-on versus prior-off before publishing a new package.

2. **Build short actual-client scenarios from the failures already recorded.** Start with entering and leaving the Goldshire trainer, exiting Stormwind water, acquiring/facing/looting an obscured target, and completing a level-appropriate objective after interrupted travel. Each scenario needs an observed destination or UI outcome, a time limit, a safe stop and saved frames/inputs. Replaying telemetry is useful regression evidence but cannot substitute for completing the scenario through the real client.

3. **Fix one live bottleneck at a time.** Measure complete service trips, useful quest/XP progress and recovery—not just kills, successful processes or test counts. In this latest sample, travel and services occupied two thirds of time. Faster spell selection alone cannot repair that result. Require a successful return to productive play after a service visit before considering its recovery complete.

4. **Use the hive for explicit questions that share execution logic.** A smaller exploratory cohort, for example 20–40 relevant characters, can investigate service eligibility, quest-state loops, pull policy or supply economics. This is an initial resource recommendation, not a claim that 20–40 characters provide enough statistical power. Size qualification trials from observed variability and independent assignment units. Keep the comparison contract identical in both arms.

5. **Qualify transfer on matched live episodes.** Use the existing comparison/release tooling with fresh actual-client outcomes. Measure completion rate, elapsed time to a specified useful endpoint, deaths, time without progress and operator interventions. Preserve failed and unfinished episodes. Repeat successful candidates from comparable starting conditions, and collect a human reference on those same tasks before making human-speed claims.

6. **Track development benefit itself.** For each hive-discovered issue, record the linked live failure, time to diagnosis, time to fix, whether the hive predicted the direction of the live result, and the live regression it prevented. A hive run without a named hypothesis or a learning artifact awaiting a transfer test should not be counted as progress toward the product.

The next milestone should be repeated useful play through the mage's known trouble spots, with bounded recovery and no operator rescue. The full evaluation leaves game services, promotion holds and deployed behavior unchanged; its deliverable is the evidence and this recommended change of direction.
