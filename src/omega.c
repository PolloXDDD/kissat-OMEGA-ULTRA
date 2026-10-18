// OMEGA V2: bounded two-hop implication graph phase guidance.
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
  const unsigned max_depth = (unsigned) GET_OPTION (omegadepth);
  const unsigned max_width = (unsigned) GET_OPTION (omegawidth);
  unsigned remaining = (unsigned) GET_OPTION (omegabudget);

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
  if (!GET_OPTION (omega) || !GET_OPTION (omegabudget) ||
      !solver->watching || solver->warming)
    return 0;
  assert (VALID_INTERNAL_INDEX (idx));
  assert (!VALUE (LIT (idx)));

  // Selective probing avoids repeated two-hop graph walks when there
  // is no sufficiently connected local structure to investigate.
  const unsigned every = (unsigned) GET_OPTION (omegaevery);
  if (every > 1 && solver->statistics.decisions % every)
    return 0;
  const unsigned positive_lit = LIT (idx);
  const unsigned negative_lit = NOT (positive_lit);
  const size_t incident = SIZE_WATCHES (WATCHES (positive_lit)) +
                          SIZE_WATCHES (WATCHES (negative_lit));
  if (incident < (size_t) GET_OPTION (omegaminwatch))
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

  const unsigned gap = (unsigned) GET_OPTION (omegagap);
  if (positive.score > negative.score &&
      positive.score - negative.score >= gap)
    return 1;
  if (negative.score > positive.score &&
      negative.score - positive.score >= gap)
    return -1;

  // An inconclusive trace defers to the original Kissat phase saving.
  return 0;
}
