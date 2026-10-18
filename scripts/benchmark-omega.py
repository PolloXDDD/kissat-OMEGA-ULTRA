#!/usr/bin/env python3
"""A/B runner for OMEGA versus unmodified phase selection, same Kissat build.

Runs --omega=0 and --omega=1 on repository CNFs, validates exit status,
checks SAT assignments when output includes a full 'v ... 0' witness,
and writes a portable CSV. This is a reproducible test, not an assertion
that OMEGA is always faster.
"""
import argparse
import csv
import pathlib
import shlex
import subprocess
import time


def clauses_from_dimacs(path):
    clauses, clause = [], []
    declared = None
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("c"):
            continue
        if line.startswith("p"):
            words = line.split()
            declared = int(words[1] == "cnf") and int(words[2])
            continue
        for word in line.split():
            lit = int(word)
            if lit:
                clause.append(lit)
            else:
                clauses.append(clause)
                clause = []
    if clause:
        raise ValueError(f"Unterminated clause: {path}")
    return declared, clauses


def verify_witness(output, path):
    assignment = {}
    for line in output.splitlines():
        if line.startswith("v "):
            for item in line[2:].split():
                lit = int(item)
                if lit:
                    assignment[abs(lit)] = lit > 0
    if not assignment:
        return "no witness"
    count, clauses = clauses_from_dimacs(path)
    if count is not None and len(assignment) < count:
        return "partial witness"
    for clause in clauses:
        if not any(assignment.get(abs(x)) == (x > 0) for x in clause):
            return "INVALID WITNESS"
    return "verified"


def run_solver(binary, path, enabled, timeout, extra_args=()):
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            [str(binary), "--omega=" + str(enabled), *extra_args, str(path)],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=timeout,
        )
        elapsed = time.perf_counter() - started
        if proc.returncode == 10:
            status = "SAT"
        elif proc.returncode == 20:
            status = "UNSAT"
        else:
            status = f"EXIT_{proc.returncode}"
        witness = verify_witness(proc.stdout, path) if status == "SAT" else ""
        return status, elapsed, witness
    except subprocess.TimeoutExpired:
        return "TIMEOUT", time.perf_counter() - started, ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", default="build/kissat")
    parser.add_argument("--dir", default="test/cnf")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--cases", default="", help="comma-separated CNF basenames")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--csv", default="omega-benchmark.csv")
    parser.add_argument("--omega-args", default="", help="additional options for OMEGA mode, e.g. --omegadepth=1")
    args = parser.parse_args()
    binary = pathlib.Path(args.binary).resolve()
    tests = pathlib.Path(args.dir)
    if args.cases:
        cnfs = [tests / name.strip() for name in args.cases.split(",") if name.strip()]
    else:
        cnfs = sorted(tests.glob("*.cnf"))
    if args.limit:
        cnfs = cnfs[:args.limit]
    if not binary.is_file():
        parser.error(f"Missing solver: {binary}; first run ./configure && make -C build")
    rows = []
    problems = 0
    extra_args = shlex.split(args.omega_args)
    for path in cnfs:
        if not path.is_file():
            raise FileNotFoundError(path)
        base = run_solver(binary, path, 0, args.timeout)
        omega = run_solver(binary, path, 1, args.timeout, extra_args)
        consistent = (base[0] == omega[0] and base[0] in ("SAT", "UNSAT"))
        valid = base[2] != "INVALID WITNESS" and omega[2] != "INVALID WITNESS"
        if not consistent or not valid:
            problems += 1
        speedup = base[1] / omega[1] if omega[1] else float("inf")
        row = {
            "cnf": path.name, "baseline": base[0], "omega": omega[0],
            "baseline_s": f"{base[1]:.6f}", "omega_s": f"{omega[1]:.6f}",
            "speedup": f"{speedup:.3f}", "consistent": consistent,
            "baseline_witness": base[2], "omega_witness": omega[2],
        }
        rows.append(row)
        print(f"{path.name:30} {base[0]:9} {omega[0]:9} "
              f"base={base[1]:8.4f}s omega={omega[1]:8.4f}s "
              f"x{speedup:6.2f} {'OK' if consistent and valid else 'CHECK'}",
              flush=True)
    if not rows:
        parser.error("No CNFs selected")
    with open(args.csv, "w", newline="") as fd:
        writer = csv.DictWriter(fd, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Cases: {len(rows)} | disagreements/timeouts/invalid models: {problems}")
    print(f"Total baseline: {sum(float(x['baseline_s']) for x in rows):.4f}s")
    print(f"Total OMEGA:    {sum(float(x['omega_s']) for x in rows):.4f}s")
    print(f"CSV: {args.csv}")
    if problems:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
