// OMEGA V3: mandatory native XOR regime plus bounded implication guidance.
//
// A decision x=true falsifies -x. Binary clauses (-x v y) then imply y.
// OMEGA explores a bounded portion of this implication graph, compares both
// decision polarities, and recommends a phase only when its signal is strong.
// This is strictly a heuristic: it never assigns values, adds clauses,
// changes conflict analysis, or claims polynomial-time SAT solving.

#include "omega.h"
#include "inlinevector.h"
#include "internal.h"

#include <assert.h>
#include <limits.h>
#include <stdbool.h>

#define OMEGA_MAX_WIDTH 64

typedef struct omega_pressure omega_pressure;
struct omega_pressure {
  unsigned score;
  bool contradiction;
};

static omega_pressure trace_implications (kissat *solver,
                                          unsigned decision_lit) {
  omega_pressure res = {0, false};
  const unsigned max_depth = 2;
  const unsigned max_width = 16;
  unsigned remaining = 64;

  assert (max_width <= OMEGA_MAX_WIDTH);
  unsigned queue[OMEGA_MAX_WIDTH + 1];
  unsigned char depth[OMEGA_MAX_WIDTH + 1];
  unsigned queued = 1;
  queue[0] = decision_lit;
  depth[0] = 0;

  // There are at most 'omegabudget' visited watch heads in this trace.
  // Binary watches encode one entry; large clauses use two entries.
  for (unsigned cursor = 0; cursor < queued && remaining; ++cursor) {
    if (depth[cursor] >= max_depth)
      continue;
    const unsigned falsified = NOT (queue[cursor]);
    watches *ws = &WATCHES (falsified);
    const watch *p = BEGIN_WATCHES (*ws);
    const watch *const end = END_WATCHES (*ws);
    while (p < end && remaining) {
      const watch w = *p++;
      --remaining;
      if (!w.type.binary) {
        // Skip the reference following a large-clause blocking watch.
        if (p < end)
          ++p;
        continue;
      }

      const unsigned other = w.binary.lit;
      const value assigned = VALUE (other);
      if (assigned > 0)
        continue;
      if (assigned < 0) {
        res.contradiction = true;
        return res;
      }

      bool found = false;
      for (unsigned k = 0; k < queued; ++k) {
        if (queue[k] == other) {
          found = true;
          break;
        }
        if (queue[k] == NOT (other)) {
          res.contradiction = true;
          return res;
        }
      }

      if (!found && queued <= max_width) {
        queue[queued] = other;
        depth[queued] = depth[cursor] + 1;
        ++queued;
        // Direct propagation receives greater weight than the second hop.
        res.score += depth[cursor] == 0 ? 4 : 1;
      }
    }
  }
  return res;
}

int kissat_omega_decide_phase (kissat *solver, unsigned idx) {
  if (!solver->watching || solver->warming)
    return 0;
  assert (VALID_INTERNAL_INDEX (idx));
  assert (!VALUE (LIT (idx)));

  // Selective probing avoids repeated two-hop graph walks when there
  // is no sufficiently connected local structure to investigate.
  const unsigned every = 8;
  if (every > 1 && solver->statistics.decisions % every)
    return 0;
  const unsigned positive_lit = LIT (idx);
  const unsigned negative_lit = NOT (positive_lit);
  const size_t incident = SIZE_WATCHES (WATCHES (positive_lit)) +
                          SIZE_WATCHES (WATCHES (negative_lit));
  if (incident < 6)
    return 0;
  const omega_pressure positive = trace_implications (solver, positive_lit);
  const omega_pressure negative =
      trace_implications (solver, negative_lit);

  // If just one sampled implication graph contains a contradiction,
  // favor the other polarity. No unit clause is silently inferred.
  if (positive.contradiction != negative.contradiction)
    return positive.contradiction ? -1 : 1;
  if (positive.contradiction)
    return 0;

  const unsigned gap = 3;
  if (positive.score > negative.score &&
      positive.score - negative.score >= gap)
    return 1;
  if (negative.score > positive.score &&
      negative.score - positive.score >= gap)
    return -1;

  // An inconclusive trace defers to the original Kissat phase saving.
  return 0;
}

// OMEGA XOR-SENSE: recognize complete four-clause 3-variable parity gates
// from original DIMACS input.  No constraint is modified by this classifier.
void kissat_omega_observe_external_literal (kissat *solver, int elit) {
  if (elit) {
    if (solver->omega_clause_arity < 3)
      solver->omega_clause[solver->omega_clause_arity] = elit;
    if (solver->omega_clause_arity < 4)
      solver->omega_clause_arity++;
    return;
  }
  const unsigned n = solver->omega_clause_arity;
  solver->omega_clause_arity = 0;
  if (n != 3) {
    solver->omega_xor_mask = 0;
    return;
  }
  int lit[3];
  for (unsigned i = 0; i < 3; i++) {
    lit[i] = solver->omega_clause[i];
    if (!lit[i] || lit[i] == INT_MIN) {
      solver->omega_xor_mask = 0;
      return;
    }
  }
  // Sort three signed literals by absolute external variable index.
  for (unsigned i = 1; i < 3; i++) {
    const int v = lit[i];
    const unsigned key = v < 0 ? -(unsigned) v : (unsigned) v;
    unsigned j = i;
    while (j) {
      const int prev = lit[j - 1];
      const unsigned absprev =
          prev < 0 ? -(unsigned) prev : (unsigned) prev;
      if (absprev <= key)
        break;
      lit[j] = prev;
      j--;
    }
    lit[j] = v;
  }
  unsigned ids[3], signs = 0;
  for (unsigned i = 0; i < 3; i++) {
    ids[i] = lit[i] < 0 ? -(unsigned) lit[i] : (unsigned) lit[i];
    if (lit[i] < 0)
      signs |= 1u << i;
  }
  if (ids[0] == ids[1] || ids[1] == ids[2]) {
    solver->omega_xor_mask = 0;
    return;
  }
  const bool same =
      solver->omega_xor_mask &&
      ids[0] == solver->omega_xor_signature[0] &&
      ids[1] == solver->omega_xor_signature[1] &&
      ids[2] == solver->omega_xor_signature[2];
  const unsigned bit = 1u << signs;
  if (!same || (solver->omega_xor_mask & bit)) {
    solver->omega_xor_signature[0] = ids[0];
    solver->omega_xor_signature[1] = ids[1];
    solver->omega_xor_signature[2] = ids[2];
    solver->omega_xor_mask = bit;
  } else
    solver->omega_xor_mask |= bit;

  // Odd-negation parity uses masks 1,2,4,7 -> 0x96.
  // Even-negation parity uses masks 0,3,5,6 -> 0x69.
  if (solver->omega_xor_mask == 0x96u ||
      solver->omega_xor_mask == 0x69u) {
    solver->omega_xor_gates++;
    solver->omega_xor_mask = 0;
  }
}

bool kissat_omega_xor_dominated (kissat *solver) {
  // Structural auto-profile, not a user option.  Ordinary CNFs retain
  // their native Kissat search mode.
  return solver->omega_xor_gates >= 8192u;
}
