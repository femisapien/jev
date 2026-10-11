#!/usr/bin/env python3
"""Compare independently matched episodes; reads an explicit JSON sample set, no game input."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from jev.learn.comparison import compare
from jev.learn.provenance import artifact

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('samples', type=Path)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    doc = json.loads(args.samples.read_text())
    result = compare(doc['samples'])
    result.update(samples=doc['samples'], source=artifact(args.samples))
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
