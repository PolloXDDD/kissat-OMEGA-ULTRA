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
BIN=pathlib.Path("build/kissat").resolve()
SEEDS=(0,)
SETS=[
 ("default",[]),
 ("randec0",["--randec=0"]),
 ("randec0_phase0",["--randec=0","--phase=0"]),
 ("phase0",["--phase=0"]),
 ("target0",["--target=0"]),
 ("target2",["--target=2"]),
 ("no_saved_phase",["--phasesaving=0"]),
 ("stable0",["--stable=0"]),
 ("stable2",["--stable=2"]),
 ("stable2_randec0",["--stable=2","--randec=0"]),
 ("stable0_randec0",["--stable=0","--randec=0"]),
 ("restartint10",["--restartint=10"]),
 ("restartint50",["--restartint=50"]),
 ("restartmargin0",["--restartmargin=0"]),
 ("restartmargin25",["--restartmargin=25"]),
 ("chronological_off",["--chrono=0"]),
 ("rephase_off",["--rephase=0"]),
 ("reorder_off",["--reorder=0"]),
 ("target0_randec0",["--target=0","--randec=0"]),
 ("phase0_stable0",["--phase=0","--stable=0"]),
 ("phase0_stable2",["--phase=0","--stable=2"]),
 ("reduce_high",["--reducehigh=800"]),
 ("bump_reason_off",["--bumpreasons=0"]),
 ("congruence_xor_only",["--congruencexors=1","--congruenceands=0","--congruenceites=0"]),
]
def metric(text,name):
    m=re.findall(r"(?m)^c\s+([\d,]+)\s+"+name+r"(?:\s|$)",text)
    return int(m[-1].replace(",","")) if m else None
def run(label,opts,seed):
    cmd=[str(BIN),"--seed="+str(seed),"--decisions=10000","--time=30","-s",*opts,str(CNF)]
    t=time.perf_counter()
    proc=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                        text=True,timeout=42)
    out=proc.stdout
    row=dict(variant=label,seed=seed,exit_code=proc.returncode,
             seconds=round(time.perf_counter()-t,5),
             decisions=metric(out,"decisions"),conflicts=metric(out,"conflicts"),
             propagations=metric(out,"propagations"),
             restarts=metric(out,"restarts"))
    print(f"{label:23} conflicts={row['conflicts']:6} decisions={row['decisions']:6} time={row['seconds']:.3f}s",flush=True)
    return row
rows=[run(name,args,seed) for seed in SEEDS for name,args in SETS]
path=pathlib.Path("benchmarks/results/sha3-ablation.csv")
path.parent.mkdir(exist_ok=True,parents=True)
with path.open("w",newline="") as f:
    writer=csv.DictWriter(f,fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
valid=[r for r in rows if r["decisions"]==10000 and r["conflicts"] is not None]
for row in sorted(valid,key=lambda x:(x["conflicts"],x["seconds"]))[:8]:
    print("BEST_CANDIDATE",row["variant"],row["conflicts"],row["seconds"])
if len(valid)!=len(rows):
    raise SystemExit("some ablations did not reach the equal decision budget")
