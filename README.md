[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

The Kissat SAT Solver
=====================

Kissat is a "keep it simple and clean bare metal SAT solver" written in C.
It is a port of CaDiCaL back to C with improved data structures, better
scheduling of inprocessing and optimized algorithms and implementation.

Coincidentally "kissat" also means "cats" in Finnish.

Run `./configure && make test` to configure, build and test in `build`.

Binaries are provided with each major [release](https://github.com/arminbiere/kissat/releases/).

You can get more information about Kissat in the last solver description for the SAT Competition 2024:

<p>
<a href="https://cca.informatik.uni-freiburg.de/biere/index.html#publications">Armin Biere</a>,
<a href="/biere/index.html">Tobias Faller</a>,
Katalin Fazekas,
<a href="https://cca.informatik.uni-freiburg.de/fleury/index.html">Mathias Fleury</a>,
Nils Froleyks
and
<a href="https://cca.informatik.uni-freiburg.de/pollittf.html">Florian Pollitt</a>
<br>
<a href="https://cca.informatik.uni-freiburg.de/papers/BiereFallerFazekasFleuryFroleyksPollitt-SAT-Competition-2024-solvers.pdf">CaDiCaL, Gimsatul, IsaSAT and Kissat Entering the SAT Competition 2024</a>
<br>
<i>Proc.&nbsp;SAT Competition 2024: Solver, Benchmark and Proof Checker Descriptions</i>
<br>
Marijn Heule, Markus Iser, Matti J&auml;rvisalo, Martin Suda (editors)
<br>
Department of Computer Science Report Series B
<br>
vol.&nbsp;B-2024-1,
pages 8-10,
University of Helsinki 2024
<br>
[ <a href="https://cca.informatik.uni-freiburg.de/papers/BiereFallerFazekasFleuryFroleyksPollitt-SAT-Competition-2024-solvers.pdf">paper</a>
| <a href="https://cca.informatik.uni-freiburg.de/papers/BiereFallerFazekasFleuryFroleyksPollitt-SAT-Competition-2024-solvers.bib">bibtex</a>
| <a href="https://github.com/arminbiere/cadical">cadical</a>
| <a href="https://github.com/arminbiere/kissat">kissat</a>
| <a href="https://github.com/arminbiere/gimsatul">gimsatul</a>
| <a href="https://cca.informatik.uni-freiburg.de/sat24medals">medals</a>
]
</p>

See [NEWS.md](NEWS.md) for feature updates.

## Kissat OMEGA V3 — fully integrated XOR regime

This is **the original Kissat CDCL solver plus mandatory extra algorithms**.
Native Kissat's existing propagation, branching, learned clauses, restarts,
proof support and simplifications remain intact. The OMEGA extensions are
enabled automatically in every build; there is no `--omega` switch.

### New built-in algorithms

**OMEGA XOR-SENSE:** recognizes full four-clause ternary XOR encodings during
original DIMACS ingestion. A complete 0x96/0x69 sign mask is required; arbitrary
triples of variables are never treated as parity gates.

**OMEGA automatic XOR regime:** when >=8192 verified XOR gates have been
detected, Kissat automatically uses a zero-margin glue-responsive restart
threshold **and** full nonchronological backjumping. They act together because
empirical tests found the restart policy by itself could increase conflicts.
For other formulas, Kissat retains its native restart/backjump policies.

**OMEGA bounded binary lookahead:** the original V2 module remains integrated
and active by default. It estimates a small two-hop binary implication
neighborhood for decision phases, limited to 64 watch visits per polarity
and sampled every eight decisions. Inconclusive proposals defer to Kissat.

These changes are **heuristic guidance**, not additional unproven inference
rules: all SAT/UNSAT decisions still come from the original sound CDCL core.

### Build and solve the exact uploaded SHA-3 collision problem

```bash
./configure && make -C build -j2
python3 scripts/generate-sha3-collision.py
./build/kissat benchmarks/sha3_collision_5.cnf
```

The deterministic generator recreates the supplied
`sha3_collision (5).cnf` **byte-for-byte** (25,969,569 bytes):

```
SHA256 249ad83e8f3198d1dcc580cfaec023c5078ba24378fe7337c798158b338bcead
variables 310636; clauses 1156185; detected XOR quartets 230464
```

The CNF models two 64-bit messages through complete **Keccak-f[1600],
24 rounds**, equates their 256-bit digests and requires distinct inputs.
It is a very difficult cryptographic SAT instance. Do not confuse a
bounded UNKNOWN result with a collision found or an UNSAT proof.

### SUPREME benchmark: matched decision budgets

The baseline is a separate binary built from untouched Kissat. OMEGA's
features remain integrated in the modified binary at all times.

```bash
git worktree add --detach baseline 8af8e56f174b778aef3aa45af9f739b2a5f492c2
(cd baseline && ./configure && make -C build -j2)
python3 scripts/benchmark-sha3-supreme.py --decisions 50000 --seeds 0,1,2
python3 scripts/benchmark-omega.py --limit 50
```

Both GitHub Actions workflows automatically compile, test and benchmark the
solvers. SHA3 SUPREME writes full raw logs, CSV and Markdown results as
downloadable Actions artifacts. The benchmark reports conflicts after an
**equal number of decisions**, plus wall time, propagations and solution status.
A lower conflict count is only a trajectory metric: it is not by itself a
guarantee of better runtime or improved asymptotic complexity.

Before native integration, an ablation of the combined XOR regime against
stock Kissat achieved **216 → 74 conflicts after 10,000 decisions** and
**307 → 258 after 50,000 decisions**, across seeds 0, 1 and 2. These
numbers describe exploratory settings; refer to the most recent GitHub
Actions result for confirmation on the fully integrated executable.
