#ifndef _omega_h_INCLUDED
#define _omega_h_INCLUDED

#include <stdbool.h>

struct kissat;

void kissat_omega_observe_external_literal (struct kissat *, int lit);
bool kissat_omega_xor_dominated (struct kissat *);

// Returns -1 or +1 for a sufficiently confident phase recommendation,
// otherwise 0 so Kissat's ordinary phase selection remains in charge.
int kissat_omega_decide_phase (struct kissat *, unsigned idx);

#endif
