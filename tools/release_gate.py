#!/usr/bin/env python3
"""Validate immutable test and matched-client evidence before a release.

Standalone so deploy.sh can execute this exact candidate's gate before merging it.
This command reads evidence only; it never opens the game or changes a rollout switch.
"""
import argparse
import hashlib
import json
import math
import random
import statistics
from pathlib import Path
import time
import xml.etree.ElementTree as ET

SCENARIOS = {"quest-log", "cross-zone-supplies", "interrupted-approach", "recovery",
             "flight", "indoor-navigation"}
MATCH = ("realm", "client_build", "class", "level", "gear", "route", "rested_xp", "money", "latency_band", "crowding_band")


def checked_file(ref):
    path = Path(ref["path"])
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    if h.hexdigest() != ref["sha256"]:
        raise ValueError(f"evidence changed: {path}")
    return path


def check(record, commit, *, now=None):
    now = time.time() if now is None else now
    if record.get("commit") != commit or record.get("format") != 1:
        raise ValueError("release record does not identify this exact commit")
    if not 0 <= now - record.get("created_at", 0) <= 7 * 86400:
        raise ValueError("release evidence is stale or dated in the future")
    if not record.get("suites"):
        raise ValueError("release has no test evidence")
    for suite in record["suites"]:
        if suite.get("commit") != commit or suite.get("dirty") is not False:
            raise ValueError("test suite does not bind clean candidate code")
        if not 0 <= now - suite.get("created_at", 0) <= 7 * 86400:
            raise ValueError("test evidence is stale")
        doc = ET.parse(checked_file(suite)).getroot()
        groups = [doc] if doc.tag == "testsuite" else doc.findall("testsuite")
        if (not groups or not sum(int(g.get("tests", 0)) for g in groups)
                or any(int(g.get(k, 0)) for g in groups for k in ("errors", "failures"))):
            raise ValueError("test evidence is empty or contains failures")
    hive = json.loads(checked_file(record["hive_verdict"]).read_text())
    if hive.get("protocol") != 2 or hive.get("status") not in ("improved", "noninferior"):
        raise ValueError("hive result is not a qualified protocol-2 comparison")
    window = hive.get("window", [])
    if len(window) != 2 or window[1] <= window[0] or not 0 <= now - window[1] <= 7 * 86400:
        raise ValueError("hive comparison has no recent completed window")
    contract_ref = {"path": hive["trial_manifest"], "sha256": hive["trial_manifest_sha256"]}
    contract = json.loads(checked_file(contract_ref).read_text())
    if contract.get("candidate") != commit:
        raise ValueError("hive evidence measured a different candidate")
    if (hive.get("status") == "noninferior"
            and (contract.get("target") or {}).get("kind") != "correctness"):
        raise ValueError("an optimization needs measured improvement, not just noninferiority")
    seen = set()
    for pair in record.get("client_pairs", []):
        scenario = pair["scenario"]
        outcome = json.loads(checked_file(pair["result"]).read_text())
        samples = outcome.get("samples", [])
        if len(samples) < 8 or len({s["unit"] for s in samples}) != len(samples):
            raise ValueError(f"{scenario}: need at least eight independent matched units")
        ratios = []
        used_runs = set()
        for sample in samples:
            conditions, seconds, deaths = [], [], []
            for arm, expected in (("candidate", commit), ("control", contract["control"])):
                measured = sample[arm]
                run_ref = measured["manifest"]
                run = json.loads(checked_file(run_ref).read_text())
                identity = (arm, run.get("run_id"))
                if not identity[1] or identity in used_runs:
                    raise ValueError(f"{scenario}: repeated or missing recorded run identity")
                used_runs.add(identity)
                if not 0 <= now - run.get("started_at", 0) <= 7 * 86400:
                    raise ValueError(f"{scenario}: client evidence is stale")
                env = run.get("environment", {})
                if (env.get("tier") != "live-client" or env.get("code", {}).get("commit") != expected
                        or env["code"].get("dirty") is not False):
                    raise ValueError(f"{scenario}: run tier, code or cleanliness does not match")
                evidence = json.loads(checked_file(measured["episode"]).read_text())
                if (evidence.get("manifest_sha256") != run_ref["sha256"]
                        or evidence.get("scenario") != scenario
                        or evidence.get("unit") != sample["unit"]):
                    raise ValueError(f"{scenario}: episode is not bound to this run and unit")
                # Keep the full execution trace bound to the verified episode summary.
                checked_file(evidence["trace"])
                duration = evidence["ended_at"] - evidence["started_at"]
                if (not math.isfinite(duration) or duration <= 0
                        or evidence.get("success") is not True
                        or duration != measured.get("seconds")
                        or evidence.get("deaths") != measured.get("deaths")
                        or not isinstance(evidence["deaths"], int) or evidence["deaths"] < 0):
                    raise ValueError(f"{scenario}: incomplete or inconsistent episode evidence")
                conditions.append(evidence.get("conditions", {}))
                seconds.append(duration)
                deaths.append(evidence["deaths"])
            left, right = conditions
            if any(k not in left or k not in right or left[k] != right[k] for k in MATCH):
                raise ValueError(f"{scenario}: client conditions are not matched")
            if deaths[0] > deaths[1]:
                raise ValueError(f"{scenario}: candidate has more deaths")
            ratios.append(seconds[0] / seconds[1])
        rng = random.Random(11)
        bounds = sorted(statistics.mean(rng.choices(ratios, k=len(ratios))) for _ in range(4000))
        if bounds[int(4000 * .95)] > 1.05:
            raise ValueError(f"{scenario}: paired elapsed-time noninferiority is unproved")
        seen.add(scenario)
    if missing := SCENARIOS - seen:
        raise ValueError("missing matched-client scenarios: " + ", ".join(sorted(missing)))
    return {"qualified": True, "commit": commit, "scenarios": sorted(seen)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    args = parser.parse_args()
    try:
        result = check(json.loads(args.record.read_text()), args.commit)
    except (OSError, ValueError, KeyError, TypeError, ET.ParseError) as exc:
        print(f"release remains gated: {exc}")
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
