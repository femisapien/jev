#!/usr/bin/env python3
"""Produce commit-bound test evidence, or assemble a release record from measured evidence.

No subcommand plays the game, merges code, or changes a deployment switch.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from jev.learn.provenance import artifact, code


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='command',required=True)
    suite=sub.add_parser('suite')
    suite.add_argument('--output',type=Path,required=True)
    assemble=sub.add_parser('assemble')
    assemble.add_argument('--commit',required=True)
    assemble.add_argument('--suite',type=Path,action='append',required=True)
    assemble.add_argument('--hive-verdict',type=Path,required=True)
    assemble.add_argument('--client-result',action='append',default=[],help='SCENARIO=JSON')
    assemble.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    if args.command=='suite':
        before=code()
        if before.get('dirty') or 'commit' not in before:
            p.error('test qualification requires a committed, clean checkout')
        args.output.parent.mkdir(parents=True,exist_ok=True)
        xml=args.output.with_suffix('.xml')
        result=subprocess.run([sys.executable,'-m','pytest','-q',f'--junitxml={xml.resolve()}'],check=False)
        code.cache_clear()
        if code()!=before:
            p.error('code changed while tests ran; evidence cannot qualify this commit')
        doc={**artifact(xml),'commit':before['commit'],'dirty':False,'exit_code':result.returncode,
             'created_at':time.time()}
        args.output.write_text(json.dumps(doc,indent=2)+'\n')
        return result.returncode
    pairs=[{'scenario':entry.split('=',1)[0],'result':artifact(entry.split('=',1)[1])}
           for entry in args.client_result]
    doc={'format':1,'commit':args.commit,'created_at':time.time(),
         'suites':[json.loads(s.read_text()) for s in args.suite],
         'hive_verdict':artifact(args.hive_verdict),'client_pairs':pairs}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(doc,indent=2)+'\n')
    from release_gate import check
    try: check(doc,args.commit)
    except (ValueError,OSError,KeyError,TypeError) as exc:
        print(f'Record saved; release remains gated: {exc}')
        return 1
    print(f'Qualified record: {args.output}')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
