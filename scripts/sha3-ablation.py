#!/usr/bin/env python3
"""Research ablations on the exact SHA3 collision CNF.
This script tests stock Kissat knobs temporarily. They are NOT required at
runtime in the final OMEGA solver; findings guide automatic native policies.
"""
import csv
import pathlib
import re
import subprocess
import time
CNF=pathlib.Path("benchmarks/sha3_collision_5.cnf")
# The ablation matrix profiles untouched Kissat options, never disables OMEGA.
BIN=pathlib.Path("baseline/build/kissat").resolve()
SEEDS=(0,1,2)
BUDGETS=(10000,50000)
SETS=[
 ("default",[]),
 ("restartmargin0",["--restartmargin=0"]),
 ("chronological_off",["--chrono=0"]),
 ("xor_regime_combined",["--restartmargin=0","--chrono=0"]),
]
def metric(text,name):
    m=re.findall(r"(?m)^c\s+"+re.escape(name)+r":\s*([\d,]+)(?:\s|$)",text)
    return int(m[-1].replace(",","")) if m else None
def run(label,opts,seed,decisions_budget):
    cmd=[str(BIN),"--seed="+str(seed),"--decisions="+str(decisions_budget),"--time=45","-s",*opts,str(CNF)]
    t=time.perf_counter()
    proc=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                        text=True,timeout=60)
    out=proc.stdout
    row=dict(variant=label,seed=seed,decision_budget=decisions_budget,exit_code=proc.returncode,
             seconds=round(time.perf_counter()-t,5),
             decisions=metric(out,"decisions"),conflicts=metric(out,"conflicts"),
             propagations=metric(out,"propagations"),
             restarts=metric(out,"restarts"))
    print(f"{label:23} seed={seed} budget={decisions_budget} rc={row['exit_code']} conflicts={row['conflicts']} decisions={row['decisions']} time={row['seconds']:.3f}s",flush=True)
    if row["conflicts"] is None or row["decisions"] is None:
        print("MISSING METRICS / diagnostic stdout tail:", repr(out[-1200:]),flush=True)
    return row
rows=[run(name,args,seed,budget) for budget in BUDGETS for seed in SEEDS for name,args in SETS]
path=pathlib.Path("benchmarks/results/sha3-ablation.csv")
path.parent.mkdir(exist_ok=True,parents=True)
with path.open("w",newline="") as f:
    writer=csv.DictWriter(f,fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
valid=[r for r in rows if r["decisions"]==r["decision_budget"] and r["conflicts"] is not None]
for row in sorted(valid,key=lambda x:(x["conflicts"],x["seconds"]))[:8]:
    print("BEST_CANDIDATE",row["variant"],row["conflicts"],row["seconds"])
if len(valid)!=len(rows):
    raise SystemExit("some ablations did not reach the equal decision budget")
