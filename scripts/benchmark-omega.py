#!/usr/bin/env python3
"""Compare native OMEGA against an untouched separate Kissat binary."""
import argparse
import csv
import pathlib
import subprocess
import time

def run(binary,path,timeout):
    start=time.perf_counter()
    try:
        p=subprocess.run([str(binary),str(path)],stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,text=True,timeout=timeout)
        return {10:"SAT",20:"UNSAT"}.get(p.returncode,
            "EXIT_"+str(p.returncode)),time.perf_counter()-start
    except subprocess.TimeoutExpired:
        return "TIMEOUT",time.perf_counter()-start

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--binary",default="build/kissat")
    a.add_argument("--baseline",default="baseline/build/kissat")
    a.add_argument("--dir",default="test/cnf")
    a.add_argument("--cases",default="")
    a.add_argument("--timeout",type=float,default=15)
    a.add_argument("--limit",type=int,default=0)
    a.add_argument("--csv",default="omega-benchmark.csv")
    args=a.parse_args()
    original=pathlib.Path(args.baseline).resolve()
    omega=pathlib.Path(args.binary).resolve()
    for path in (original,omega):
        if not path.is_file():a.error("missing binary "+str(path))
    d=pathlib.Path(args.dir)
    cases=([d/x.strip() for x in args.cases.split(",") if x.strip()]
           if args.cases else sorted(d.glob("*.cnf")))
    if args.limit:cases=cases[:args.limit]
    if not cases:a.error("no test cases selected")
    rows=[]
    disagreements=0
    for case in cases:
        x,t1=run(original,case,args.timeout)
        y,t2=run(omega,case,args.timeout)
        agree=(x==y and x in ("SAT","UNSAT"))
        if not agree:disagreements+=1
        row=dict(cnf=case.name,baseline=x,omega=y,
                 baseline_s=f"{t1:.6f}",omega_s=f"{t2:.6f}",
                 ratio=f"{t1/t2:.3f}" if t2 else "inf",consistent=agree)
        rows.append(row)
        print(f"{case.name:30} baseline={x:8} omega={y:8} "
              f"base={t1:.4f}s omega={t2:.4f}s "
              f"{'OK' if agree else 'CHECK'}",flush=True)
    with open(args.csv,"w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Cases: {len(rows)} | disagreements/timeouts: {disagreements}")
    print(f"Total baseline: {sum(float(r['baseline_s']) for r in rows):.4f}s")
    print(f"Total OMEGA: {sum(float(r['omega_s']) for r in rows):.4f}s")
    if disagreements:raise SystemExit(1)
if __name__=="__main__":
    main()
