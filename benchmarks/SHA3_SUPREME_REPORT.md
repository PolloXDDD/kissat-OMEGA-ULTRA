# SHA3 SUPREME — authentic 24-round Keccak SAT benchmark

Source CNF: `sha3_collision (5).cnf` supplied by the project author.

**The benchmark input is exact, not a toy or a reduced-round approximation.**
`scripts/generate-sha3-collision.py` reproduces the original byte-for-byte:

- SHA-256: `249ad83e8f3198d1dcc580cfaec023c5078ba24378fe7337c798158b338bcead`
- Bytes: 25,969,569
- Variables: 310,636
- Clauses: 1,156,185
- Verified four-clause XOR parity groups: 230,464
- 64-bit message pairs, full Keccak-f[1600] 24 rounds, 256-bit digest equality and input inequality.

## Objective

Compare **untouched original Kissat** (commit `8af8e56f174b778aef3aa45af9f739b2a5f492c2`)
against **native Kissat OMEGA V3** (XOR-SENSE, structural restart/backjump policy,
and bounded binary-pressure lookahead permanently enabled).

The principal metric is **number of conflicts accumulated at a matching
decision-count budget**, accompanied by process wall-clock time, seed, and
SAT/UNSAT/UNKNOWN status. A lower conflict count after an equal number of
decisions is a *search-trajectory metric*, not a proof of overall progress.
A solver that simply propagates less can have fewer conflicts, so also inspect
time and the actual SAT/UNSAT verdict.

## Verified GitHub Actions results

GitHub Actions run:
[SHA3 SUPREME — three seeds and 500k decisions](https://github.com/PolloXDDD/kissat-OMEGA-ULTRA/actions/runs/39104197157)

| Decision budget | Seed | Original conflicts | OMEGA conflicts | Conflict reduction | Original wall time (s) | OMEGA wall time (s) | Result |
|---:|---:|---:|---:|---:|---:|---:|---|
| 10,000 | 0 | 216 | 74 | 65.74% | 1.50 | 1.56 | UNKNOWN / UNKNOWN |
| 10,000 | 1 | 216 | 74 | 65.74% | 1.48 | 1.51 | UNKNOWN / UNKNOWN |
| 10,000 | 2 | 216 | 74 | 65.74% | 1.50 | 1.51 | UNKNOWN / UNKNOWN |
| 50,000 | 0 | 309 | 258 | 16.50% | 1.50 | 1.48 | UNKNOWN / UNKNOWN |
| 50,000 | 1 | 309 | 258 | 16.50% | 1.49 | 1.51 | UNKNOWN / UNKNOWN |
| 50,000 | 2 | 309 | 258 | 16.50% | 1.51 | 1.47 | UNKNOWN / UNKNOWN |
| 150,000 | 0 | 799 | 444 | 44.43% | 1.55 | 1.53 | UNKNOWN / UNKNOWN |
| 150,000 | 1 | 794 | 444 | 44.08% | 1.56 | 1.59 | UNKNOWN / UNKNOWN |
| 150,000 | 2 | 788 | 444 | 43.65% | 1.59 | 1.53 | UNKNOWN / UNKNOWN |
| 500,000 | 0 | 6,032 | 2,743 | **54.53%** | 3.31 | 2.34 | UNKNOWN / UNKNOWN |

The 500k run used about **29% less wall time** as well as fewer conflicts.
The reported times are single CI measurements; startup/parsing can dominate
small budgets. These figures should be repeated and stress-tested before
asserting a statistically general runtime advantage.

The 500k case has *not* produced a SAT witness or an UNSAT proof. No complete
SHA-3 collision has been established.

## Reproduce

```sh
./configure
make -C build -j2
python3 scripts/generate-sha3-collision.py
git worktree add --detach baseline 8af8e56f174b778aef3aa45af9f739b2a5f492c2
(cd baseline && ./configure && make -C build -j2)

python3 scripts/benchmark-sha3-supreme.py --decisions 10000 --seeds 0,1,2 --out benchmarks/results/10k
python3 scripts/benchmark-sha3-supreme.py --decisions 50000 --seeds 0,1,2 --out benchmarks/results/50k
python3 scripts/benchmark-sha3-supreme.py --decisions 150000 --seeds 0,1,2 --out benchmarks/results/150k
python3 scripts/benchmark-sha3-supreme.py --decisions 500000 --time 75 --seeds 0 --out benchmarks/results/500k
```

Results, stdout logs, and machine-readable CSV are included in the linked
GitHub Actions **sha3-supreme-results** artifact. The workflow also verifies
the SHA-256 hash and, in the subsequent regression, asserts that the native
structural detector counts precisely 230,464 XOR gates.

## Correctness regression

The companion native OMEGA regression workflow compiled successfully,
passed **869 original Kissat internal test jobs** and matched the untouched
baseline's SAT/UNSAT status on **33 bundled CNFs** (no disagreements).
The structural algorithm changes branching/restarting, not satisfiability
semantics: original Kissat's CDCL conflict analysis and proof-handling remain.

## Research notes

This is an empirical heuristic extension. It is not a proof of P=NP and does
not guarantee fewer conflicts on every problem. The new XOR-SENSE profile
identifies exact parity quartet patterns and automatically couples sensitive
LBD/glue restarts with nonchronological backjumping above a conservative
structural threshold of 8,192 gates. It has no user-facing activation switches.

Further validation should include different circuit-based SAT classes,
more seeds, wall-clock variance, learnt clause LBD statistics, and proof
checking for any UNSAT outcome.
