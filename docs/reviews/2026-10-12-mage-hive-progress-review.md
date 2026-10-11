# Mage and hive progress review — 12 October 2026

The mage reached level 17, then spent 27.4 minutes without XP while attempting services and circling in Stormwind's water. It was active but stuck. The last restart's successful attachment and vendor repair were evidence of recovery only, not evidence of sustained speed.

| Finding | Evidence | Action |
| --- | --- | --- |
| Windows session handovers now survive | Three complete native sessions shared Windows PID 82440 and exited cleanly | Retain the single-process session controller; WSL memory issue remains a host limitation |
| Optional purchases retry after each session | Wand's one-hour retry deadline lived only in the body instance; 8.47 minutes spent on failed wand trips | Persist wand/weapon deadlines before attempting the visit, restore them on handover, and recognize previous failure evidence |
| Local unstick movement hides a prolonged stall | Mage oscillated along Stormwind walls and in the canal | Share one 90-second/40-yard headway budget across route legs and replans; preserve consecutive wedge evidence so existing hearth recovery can run |
| Shadow service planning can inherit cancellation | Trip service filtering called the worker's reader from the supervisor | Use the supplied observation and zone; regression test retains cross-zone merchant selection without reading a cancelled worker |
| Hive control receives disproportionate session cancellations | Current log audit found 26 control `playhead changed` exceptions versus 4 candidate; the old flight-discovery adapter calls the cancelled worker reader | Repair the adapter to use observed character race; close the incomplete comparison as inconclusive and begin a fresh fixed comparison |
| Hive results cannot establish live controller speed | Even with all observation-parity switches enabled, hive movement uses server actions and cliff checks, rather than the live keyboard follower | Require live route completion, XP and encounter measurements; keep trip planning in shadow and automatic promotion blocked |
| Model diagnosis unavailable | Coach status records weekly provider quota exhaustion, reset 14 October at 04:00 London | Retain evidence reports and the existing retry; no claim that model-driven diagnosis is working |

Before intervention, 51.15 recorded minutes produced 18 fight kills and two deaths, moving from level 16 at 90.55% to level 17 at 0%. Armed-skill time included 14.83 minutes on wand/trainer visits. `GRIND_UNTIL` time includes movement, combat and searching, so it is not a pure combat-time measurement.

Recovery used the mage's ordinary hearthstone under the exclusive native input lease, with the supervisor stopped and character identity checked. Arrival at Lakeshire Inn was observed and the hearth cooldown recorded. No server teleport or XP adjustment was used.

The recorded canal coordinates are now a regression fixture. Replaying those observations reaches the new movement guard at 92.532 seconds. A closed-pocket simulation checks the real follower across repeated replans, and a long open route verifies that productive walks may exceed 90 seconds. This proves the guard on those cases; it does not prove that the Stormwind canal mesh now has a usable exit.

The fresh live status, exact tested commits, complete suite results, hive restart and new comparison identity are recorded alongside this review. A restart or test pass alone is not a speed improvement. A claim of improvement requires a qualified comparison plus sustained live progress.

Validation: live commit `71ff145652a2a454c931c59b680549f3a96fd16d` passed all 3,367 tests with no skips. The hive adapter fix, deployed as `f768eb6`, passed 357 tests with 59 optional-feature skips against each of the control and candidate revisions. The adapter patch is exported in `2026-10-12-hive-service-cancellation.patch`.

The replacement comparison is `1791762030529-71ff145652a2`, with a six-hour window, 210 assigned characters, candidate shards 0/3/4 and five control shards. Its candidate is the latest live commit, its control is `35ba9fd`, and both arms use the same repaired adapter, frozen inputs, full observation parity, rules coach and shadow trip planning. The previous trial remains recorded as inconclusive, without promotion.
