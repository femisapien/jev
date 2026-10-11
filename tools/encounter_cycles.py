#!/usr/bin/env python3
"""Read-only full encounter-cycle report for saved runs."""
import argparse
import json
from pathlib import Path
import statistics
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from jev.learn.cycles import cycles

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('runs', nargs='+', type=Path)
    args=p.parse_args()
    out={}
    for run in args.runs:
        rows=cycles(json.loads(line) for line in (run/'executions.jsonl').open())
        complete=[r for r in rows if not r['censored']]
        out[str(run)]={'cycles':len(complete), 'censored':len(rows)-len(complete),
                       'median_seconds':statistics.median(r['seconds'] for r in complete) if complete else None,
                       'deaths':sum(r['deaths'] for r in rows), 'observations':rows}
    print(json.dumps(out, indent=2))
