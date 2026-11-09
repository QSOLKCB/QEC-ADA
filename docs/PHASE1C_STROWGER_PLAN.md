# Phase 1C proposal — deterministic Strowger routing and replay receipts

**Status:** bounded native event-stream pilot implemented on Phase 1C branch.
The bounded new QEC-ADA receipt schema now has SHA-256-linked events
and independent Python replay. Full historical QEC-compatible schema
matching, advanced operator controls and cross-era switching remain roadmap
tasks; see [Phase 1C implementation](PHASE1C_TANNER_SPECTRAL.md).

The next distinct phase can reproduce the **classical** switching semantics
of QEC's Strowger syndrome exchange, without treating switching as quantum
correction. Reference: QSOLKCB/QEC at
`27bbc798c4e38138ca5b0fff70b15c3271a1917d`,
`src/qec/routing/strowger/{model,exchange,events,pulse,tones,receipts}.py`.

## Intended contract

1. Explicit immutable invocation input: request ID, destination, logical
   epoch, topology/selector configuration, initial linefinder/trunk states,
   fault plan and authorized operator commands. No ambient clock or RNG.
2. Deterministic mixed-radix pulse encoding, including zero as a full
   radix pulse count. Bounded stages/capacities and canonical indices.
3. First-free linefinder/trunk selection, complete path continuity and
   connector coordinates. Failed requests never publish a successful route.
4. Integer logical ticks, contiguous event sequences and deterministic
   event hashes; every release, reservation and failure transition must
   be represented in the replayable event stream.
5. Expected and observed route/check/dark tones, explicit tolerance,
   fail-closed verification. Tone equality verifies classical route
   integrity, **not** decoder mathematical validity.
6. Canonical JSON and SHA-256 identity, with an independent replay
   validator that reconstructs decisions from authenticated source inputs.
   A self-consistent hash alone cannot establish a truthful route.
7. One versioned QEC-ADA receipt schema and strict validation of all
   top-level/child keys, duplicates, types and canonical ordering. Claim
   compatibility with QEC's `qec.strowger-route-receipt.v1` only after
   byte-for-byte and semantic parity has been demonstrated.
8. Operator modes must forbid force-accept, enforce explicit authorization
   and bind every intervention into the same state/evidence chain.

## Acceptance tests

- At least one available route, busy/quarantined failures, pulse omissions
  and duplication, stuck selectors, tone mismatches, release and replay.
- Repeat all fixtures twice and require identical ordered events,
  canonical bytes and SHA-256 digests under the same inputs.
- Mutation adversaries: changed event, changed input, reordered transition,
  corrupt hash, forged self-consistent receipt, duplicate operator command.
  Independent replay must reject mismatched semantics.
- Cross-language parity against pinned Python QEC test cases when
  available; divergent optional features are declared rather than
  silently normalized.
- Physical GPU/audio/UI demos and benchmark timings remain distinct
  from canonical route or QEC correction evidence.

This phase must be a **separate PR**, and it must preserve the existing
Phase 1A and 1B decoder contracts unchanged.
