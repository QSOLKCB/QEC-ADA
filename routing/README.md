# Native deterministic routing pilot

This is a **bounded classical first-free routing selection**, not the complete
QEC Strowger exchange. It follows the source ordering principle:
first-free linefinder → first-free selector stage 1 → first-free stage 2 →
two-axis connector. Availability is an immutable 4-position Boolean vector
per stage; no partial reservation or state mutation occurs on failure.

Use `qec_ada route D1 D2 D3 D4 LLLL AAAA BBBB`.
Digits are ternary `0,1,2`. Masks are four-character strings, with `1`
meaning free and `0` meaning busy. Successful routes select the first
free resource at every stage; rejected routes expose no partial reservation.
All initial-state and address bits are explicitly passed—no ambient clocks,
randomness or hidden allocation state.

The existing QEC Strowger model also supports mixed radices, pulse timing,
fault injection, tone verification, operator commands and hash-chained receipts.
**Those are not implemented here**; no output should be interpreted as a
QEC-compatible Strowger receipt or proof of decoder correctness.
See `docs/PHASE1A_DECODER_ROUTING.md`.

## Phase 1C bounded event stream and canonical receipts

`routing/qec_strowger.*` adds a **separate** explicit-state classical
switching engine with mixed-radix 2–9 four-digit pulses, logical events,
quarantined contact states and fail-closed injected faults.

`scripts/strowger_receipt.py` builds a canonical SHA-256 event-chain
receipt from the native event trace **only after** independent Python
replay produces the same result. It can validate without the native
binary. It does not replace the historical QEC Strowger schema.
