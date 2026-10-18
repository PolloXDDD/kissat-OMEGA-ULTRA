#ifndef _omega_h_INCLUDED
#define _omega_h_INCLUDED

struct kissat;

// Returns -1 or +1 for a sufficiently confident phase recommendation,
// otherwise 0 so Kissat's ordinary phase selection remains in charge.
int kissat_omega_decide_phase (struct kissat *, unsigned idx);

#endif
