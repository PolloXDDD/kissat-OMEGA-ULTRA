#!/usr/bin/env python3
"""SUPREME SHA3 benchmark: equal decision budget (not fabricated SAT result).
Reads an exact SHA256-pinned 24-round instance, runs unmodified Kissat
versus native OMEGA on one build host, saves raw logs and machine-readable CSV.
Conflicts after equal decision counts are a search-trajectory metric, not proof
of progress or of SHA3 collision existence. Lower raw conflicts per fixed
time alone is NOT an improvement criterion.
"""
import argparse
import csv
import hashlib
import pathlib
import re
import subprocess
import sys
import time

SHA="249ad83e8f3198d1dcc580cfaec023c5078ba24378fe7337c798158b338bcead"

def hash_file(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1<<20),b""):
            h.update(block)
    return h.hexdigest()

def parse_metric(text,name):
    # Kissat -s produces lines such as 'c          123456 conflicts ...'
    pats=[
        re.compile(r"(?m)^c\s+([\d,]+)\s+"+re.escape(name)+r"(?:\s|$)"),
        re.compile(r"(?im)^c\s+"+re.escape(name)+r"\s*:\s*([\d,]+)(?:\s|$)")
    ]
    hits=[]
    for p in pats:
        hits.extend(int(x.replace(",","")) for x in p.findall(text))
    return hits[-1] if hits else None

def run(binpath,cnf,decisions,seconds,seed,logpath):
    cmd=[str(binpath),"--seed="+str(seed),"--decisions="+str(decisions),
         "--time="+str(seconds),"-s",str(cnf)]
    start=time.perf_counter()
    try:
        done=subprocess.run(cmd,text=True,stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,timeout=seconds+30)
        elapsed=time.perf_counter()-start
        out=done.stdout
        exitcode=done.returncode
    except subprocess.TimeoutExpired as exc:
        elapsed=time.perf_counter()-start
        out=(exc.stdout or b"").decode(errors="replace") if isinstance(exc.stdout,bytes) else (exc.stdout or "")
        exitcode=124
    logpath.write_text("$ "+" ".join(cmd)+"\n"+out,encoding="utf8")
    xor_match=re.search(r"OMEGA XOR-SENSE:\s*([\d,]+) verified XOR gates",out)
    xor_groups=(int(xor_match.group(1).replace(",",""))
                if xor_match else None)
    return dict(xor_groups=xor_groups,
                result={10:"SAT",20:"UNSAT",0:"UNKNOWN",124:"EXTERNAL_TIMEOUT"}.get(exitcode,"ERROR"),
                exit_code=exitcode,seconds=round(elapsed,4),
                decisions=parse_metric(out,"decisions"),conflicts=parse_metric(out,"conflicts"),
                propagations=parse_metric(out,"propagations"),
                restarts=parse_metric(out,"restarts"))

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--cnf",default="benchmarks/sha3_collision_5.cnf")
    p.add_argument("--baseline",default="baseline/build/kissat")
    p.add_argument("--omega",default="build/kissat")
    p.add_argument("--decisions",type=int,default=10000)
    p.add_argument("--time",type=int,default=45)
    p.add_argument("--seeds",default="0",help="comma-separated deterministic seeds")
    p.add_argument("--out",default="benchmarks/results")
    p.add_argument("--allow-other-cnf",action="store_true",help="Only for noncanonical experiments")
    a=p.parse_args()
    cnf=pathlib.Path(a.cnf).resolve()
    for filename in (a.baseline,a.omega):
        if not pathlib.Path(filename).is_file():
            p.error(f"missing binary: {filename}")
    if not cnf.is_file():
        p.error("SHA3 input missing: run python3 scripts/generate-sha3-collision.py")
    sha=hash_file(cnf)
    if sha!=SHA and not a.allow_other_cnf:
        p.error(f"CNF hash mismatch: {sha} != {SHA}")
    if a.decisions<1 or a.time<1:
        p.error("decisions and time must be positive")
    outdir=pathlib.Path(a.out)
    outdir.mkdir(parents=True,exist_ok=True)
    rows=[]
    for seed in map(int,a.seeds.split(",")):
        for name,path in (("kissat_original",a.baseline),("kissat_omega",a.omega)):
            logfile=outdir/f"{name}_seed{seed}.log"
            values=run(pathlib.Path(path).resolve(),cnf,a.decisions,a.time,seed,logfile)
            row={"variant":name,"seed":seed,"cnf_sha256":sha,"decision_budget":a.decisions,
                 "time_budget_s":a.time,**values,"log":str(logfile)}
            rows.append(row)
            if name=="kissat_omega" and sha==SHA and values["xor_groups"]!=230464:
                raise SystemExit(
                    f"OMEGA XOR-SENSE regression: expected 230464 detected gates, "
                    f"got {values['xor_groups']}")
            print(f"{name:18} seed={seed} result={values['result']:8} "
                  f"decisions={values['decisions']} conflicts={values['conflicts']} "
                  f"elapsed={values['seconds']:.2f}s",flush=True)
    with (outdir/"sha3-supreme.csv").open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    # Do not call lower conflict throughput under timeouts 'better'.
    byseed={}
    for row in rows:
        byseed.setdefault(row["seed"],{})[row["variant"]]=row
    report=["# SHA-3/256 full 24-round collision benchmark","",
       f"- SHA-256: \`{sha}\`",
       "- Exactly 310,636 variables, 1,156,185 clauses, 64-bit messages",
       f"- Equal decision budget: {a.decisions}; safety time cap: {a.time} seconds",
       "",
       "| Seed | Original conflicts | OMEGA conflicts | Original decisions | OMEGA decisions | Original time (s) | OMEGA time (s) | Result |",
       "|---:|---:|---:|---:|---:|---:|---:|---|"]
    for seed,pair in byseed.items():
        x,y=pair["kissat_original"],pair["kissat_omega"]
        fmt=lambda v: "n/a" if v is None else str(v)
        report.append(f"| {seed} | {fmt(x['conflicts'])} | {fmt(y['conflicts'])} | {fmt(x['decisions'])} | {fmt(y['decisions'])} | {x['seconds']} | {y['seconds']} | {x['result']} / {y['result']} |")
    report.extend(["",
       "**Interpretation:** This compares conflicts accumulated until a *matched decision-count* budget,",
       "when both runs reach it. If either hits the time cap early, conflict counts are",
       "not directly comparable. No SAT/UNSAT verdict can be inferred from UNKNOWN.",
       "A smaller conflict count does not by itself prove a faster solve or improved asymptotics.",
       "Use full raw logs and report time, propagation and resolved status together."])
    (outdir/"SHA3_SUPREME_RESULTS.md").write_text("\n".join(report)+"\n")
    print("Artifacts:",outdir/"sha3-supreme.csv",outdir/"SHA3_SUPREME_RESULTS.md")
    if any(r["result"]=="ERROR" for r in rows):
        raise SystemExit(1)

if __name__=="__main__":
    main()
