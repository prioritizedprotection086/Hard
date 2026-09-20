#!/usr/bin/env python3
"""Run adaptive adversary evaluation."""
import sys
sys.path.insert(0, ".")
from sve_dual.adversary import AdaptiveAdversary

def main():
    adv = AdaptiveAdversary(seed=7)
    report = adv.run()
    print("=" * 60)
    print("  ADAPTIVE ADVERSARY REPORT")
    print("=" * 60)
    print(f"  tested:            {report.tested}")
    print(f"  fail_open:         {report.fail_open}")
    print(f"  false_positive:    {report.false_positive}")
    print(f"  invariant_breaks:  {report.invariant_breaks}")
    print(f"  capability_leaks:  {report.capability_leaks}")
    print(f"  ok:                {report.ok}")
    if report.findings:
        print("\n  findings:")
        for f in report.findings[:30]:
            print(f"    [{f.kind}] mut={f.mutation} path={f.pathway} T={f.threat:.2f}")
            print(f"      seed={f.seed!r}")
            print(f"      text={f.mutated!r}")
            print(f"      {f.detail}")
    print("=" * 60)
    sys.exit(0 if report.ok else 1)

if __name__ == "__main__":
    main()
