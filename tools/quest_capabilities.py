#!/usr/bin/env python3
"""Read-only quest dependency and executor priority report."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from jev.guide.graph import Graph
from jev.guide.capabilities import unlock_priorities
from jev.run.body import LiveBody

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('graphs', type=Path, nargs='+')
    args = parser.parse_args()
    print(json.dumps({str(p): unlock_priorities(Graph.load(p), LiveBody.available)
                      for p in args.graphs}, indent=2))
