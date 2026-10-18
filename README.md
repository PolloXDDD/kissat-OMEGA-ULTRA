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

## OMEGA V2 experimental extension

This fork retains all native Kissat functionality, including CDCL, learned
clauses, branching heuristics, restarts, propagation, simplification, proof
handling and existing solver configurations. It **adds** a bounded binary
implication-graph phase heuristic in `src/omega.c`. OMEGA is not a separate
solver and does not replace Kissat.

**How it works.** Given an unassigned decision variable, the module traces
both polarities over watched binary clauses for up to two implication hops.
Direct implications are weighted more than second-hop implications. When a
contradiction is found for exactly one candidate polarity, the other is
preferred; otherwise OMEGA recommends the polarity with sufficiently greater
local implication pressure. If the scores are close, the ordinary Kissat
target/saved/initial phase machinery is used. The heuristic observes *current*
binary clauses, including learned clauses, but never mutates assignments or
proof state. Variable selection is still handled by native Kissat.

### Options

| Option | Default | Description |
|---|---:|---|
| `--omega=0/1` | 1 | Disable/enable OMEGA (0 restores original phase logic) |
| `--omegabudget=N` | 96 | Maximum watch entries inspected **per polarity** |
| `--omegadepth=1/2` | 2 | Implication graph traversal depth |
| `--omegagap=N` | 3 | Minimum score difference to use recommendation |
| `--omegawidth=N` | 16 | Maximum queued implied literals per polarity (1–64) |

The existing target-phase preference keeps precedence. OMEGA acts before
ordinary saved phase selection when no target preference was chosen.

### Reproducible benchmark

```sh
./configure
make -C build -j2
# Unmodified behavior for comparison:
./build/kissat --omega=0 test/cnf/add16.cnf
# Extended algorithm:
./build/kissat --omega=1 test/cnf/add16.cnf
# Test every repository instance against both modes:
python3 scripts/benchmark-omega.py --timeout 10 --csv omega-benchmark.csv
```

The A/B script records SAT/UNSAT agreement, per-instance wall clock time,
speedup ratios, and verifies emitted SAT witnesses when available. GitHub
Actions runs a selected cross-section of this repository's `test/cnf`
instances, plus the original `tissat` regression suite. The script exits
nonzero on disagreements or invalid models.

**Research status:** OMEGA V2 is an experimental heuristic inspired by local
implication-graph and structural SAT analysis. It is not a proof of P=NP,
not a worst-case complexity improvement, and not guaranteed to outperform
Kissat on every CNF. Compare both modes before drawing performance claims.
