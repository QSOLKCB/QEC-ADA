#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Ideal-syndrome CSS Pauli decoder and exact GF(2) logical-coset classifier.

Independent X/Z syndrome-only integer min-sum decoders with a deterministic
weight-one fallback. The decoder NEVER receives planted error locations.
Correlated X and Z Pauli components arise from the Y channel outcome.
This is a phenomenological ideal-syndrome model, not fault-tolerant hardware.
"""
from __future__ import annotations

from dataclasses import dataclass
import phase1e_reference as reference

NOISE_DOMAIN = "qecada.phase1i.depolarizing.v1"
PRIOR = 6
CAP = 48


def rows_of(n: int, m: int, edges: list[tuple[int, int]]) -> tuple[int, ...]:
    reference.canonical_graph(n, m, edges)
    rows = [0] * m
    for check, site in edges:
        rows[check - 1] |= 1 << (site - 1)
    return tuple(rows)


def echelon(rows: tuple[int, ...]) -> dict[int, int]:
    pivots = {}
    for original in rows:
        value = original
        while value:
            pivot = value.bit_length() - 1
            if pivot not in pivots:
                pivots[pivot] = value
                break
            value ^= pivots[pivot]
    return pivots


def in_span(value: int, pivots: dict[int, int]) -> bool:
    if type(value) is not int or value < 0:
        raise ValueError("invalid GF(2) vector")
    while value:
        pivot = value.bit_length() - 1
        if pivot not in pivots:
            return False
        value ^= pivots[pivot]
    return True


def syndrome(rows: tuple[int, ...], value: int) -> tuple[int, ...]:
    if type(value) is not int or value < 0:
        raise ValueError("invalid Pauli support")
    return tuple((r & value).bit_count() & 1 for r in rows)


def sites(value: int, n: int) -> list[int]:
    return [i for i in range(1, n + 1) if value & (1 << (i - 1))]


@dataclass(frozen=True)
class CSS:
    n: int
    xrows: tuple[int, ...]
    zrows: tuple[int, ...]
    hx: tuple[tuple[int, int], ...]
    hz: tuple[tuple[int, int], ...]
    xbasis: dict[int, int]
    zbasis: dict[int, int]
    k: int


def prepare(n: int, mx: int, hx: list[tuple[int, int]],
            mz: int, hz: list[tuple[int, int]]) -> CSS:
    if (type(n) is not int or type(mx) is not int or type(mz) is not int
            or not 1 <= n <= 128 or not 1 <= mx <= 128
            or not 1 <= mz <= 128 or len(hx) > 2048 or len(hz) > 2048):
        raise ValueError("CSS model outside native bounds")
    xrows, zrows = rows_of(n, mx, hx), rows_of(n, mz, hz)
    if any((x & z).bit_count() & 1 for x in xrows for z in zrows):
        raise ValueError("noncommuting CSS checks")
    bx, bz = echelon(xrows), echelon(zrows)
    k = n - len(bx) - len(bz)
    if k < 0:
        raise ValueError("negative CSS logical dimension")
    return CSS(n, xrows, zrows, tuple(hx), tuple(hz), bx, bz, k)


def decode_syndrome(n: int, rows: tuple[int, ...],
                    edges: tuple[tuple[int, int], ...],
                    target: tuple[int, ...], rounds: int = 14) -> dict:
    """Pure syndrome-only min-sum, then canonical single-site leader."""
    if (type(n) is not int or not 1 <= n <= 128
            or len(rows) != len(target) or not 1 <= len(rows) <= 128
            or type(rounds) is not int or not 1 <= rounds <= 50
            or any(type(v) is not int or v not in (0, 1) for v in target)):
        raise ValueError("invalid syndrome decoding request")
    if not any(target):
        return {"method": "ZERO_SYNDROME", "correction_sites": [],
                "solved": True, "rounds": 0,
                "trace": [{"round": 0, "syndrome_mismatches": 0,
                           "correction_weight": 0}]}
    checks = [[] for _ in range(len(rows) + 1)]
    variables = [[] for _ in range(n + 1)]
    for c, v in edges:
        checks[c].append(v)
        variables[v].append(c)
    messages = {(c, v): PRIOR for c, v in edges}
    tape = [{"round": 0, "syndrome_mismatches": sum(target),
             "correction_weight": 0}]
    decision = 0
    for step in range(1, rounds + 1):
        incoming = {}
        for c in range(1, len(rows) + 1):
            for v in checks[c]:
                others = [messages[(c, u)] for u in checks[c] if u != v]
                magnitude = min(map(abs, others)) if others else CAP
                negative = bool(target[c - 1] ^ (
                    sum(msg < 0 for msg in others) & 1))
                incoming[(c, v)] = -magnitude if negative else magnitude
        posterior = [0] + [
            PRIOR + sum(incoming[(c, v)] for c in variables[v])
            for v in range(1, n + 1)]
        decision = sum(1 << (v - 1) for v in range(1, n + 1)
                       if posterior[v] < 0)
        mismatches = sum(x != y for x, y in
                         zip(syndrome(rows, decision), target))
        tape.append({"round": step, "syndrome_mismatches": mismatches,
                     "correction_weight": decision.bit_count()})
        if not mismatches:
            return {"method": "SYNDROME_MIN_SUM",
                    "correction_sites": sites(decision, n), "solved": True,
                    "rounds": step, "trace": tape}
        messages = {
            (c, v): max(-CAP, min(CAP, posterior[v] - incoming[(c, v)]))
            for c, v in edges}
    for v in range(1, n + 1):
        if syndrome(rows, 1 << (v - 1)) == target:
            return {"method": "RADIUS_ONE_SYNDROME_LEADER",
                    "correction_sites": [v], "solved": True,
                    "rounds": rounds, "trace": tape}
    return {"method": "UNRESOLVED_SYNDROME",
            "correction_sites": sites(decision, n), "solved": False,
            "rounds": rounds, "trace": tape}


def pauli_tape(seed: str, code_id: str, bps: int, trial: int,
               n: int) -> list[tuple[int, str]]:
    if (not isinstance(seed, str) or not seed.isascii() or not seed
            or not isinstance(code_id, str) or not code_id.isascii()
            or not code_id or type(bps) is not int or not 0 <= bps <= 5000
            or type(trial) is not int or trial < 0 or not 1 <= n <= 128):
        raise ValueError("invalid Pauli experiment channel")
    out = []
    for site in range(1, n + 1):
        prefix = (NOISE_DOMAIN, seed, code_id, bps, trial, site)
        if reference.digest_int(*prefix, "flip") % 10000 < bps:
            kind = "XYZ"[reference.digest_int(*prefix, "type") % 3]
            out.append((site, kind))
    return out


def run_case(model: CSS, tape: list[tuple[int, str]],
             rounds: int = 14) -> dict:
    """Syndrome-only corrections plus independent residual logical test."""
    xerr = zerr = 0
    seen = set()
    for site, kind in tape:
        if (type(site) is not int or not 1 <= site <= model.n
                or site in seen or kind not in ("X", "Y", "Z")):
            raise ValueError("invalid planted Pauli tape")
        seen.add(site)
        if kind in ("X", "Y"):
            xerr |= 1 << (site - 1)
        if kind in ("Z", "Y"):
            zerr |= 1 << (site - 1)
    target_z = syndrome(model.zrows, xerr)
    target_x = syndrome(model.xrows, zerr)
    cx = decode_syndrome(model.n, model.zrows, model.hz, target_z, rounds)
    cz = decode_syndrome(model.n, model.xrows, model.hx, target_x, rounds)
    corr_x = sum(1 << (v - 1) for v in cx["correction_sites"])
    corr_z = sum(1 << (v - 1) for v in cz["correction_sites"])
    residual_x, residual_z = xerr ^ corr_x, zerr ^ corr_z
    sx_left = sum(syndrome(model.zrows, residual_x))
    sz_left = sum(syndrome(model.xrows, residual_z))
    consistent = (sx_left == 0 and sz_left == 0)
    lx = not in_span(residual_x, model.xbasis) if consistent else None
    lz = not in_span(residual_z, model.zbasis) if consistent else None
    logical = bool(lx or lz) if consistent else None
    outcome = ("DETECTED_UNRESOLVED" if not consistent
               else "NONTRIVIAL_LOGICAL" if logical
               else "STABILIZER_EQUIVALENT_SUCCESS")
    return {
        "pauli_errors": [[v, k] for v, k in tape],
        "pauli_weight": len(tape),
        "y_count": sum(kind == "Y" for _, kind in tape),
        "true_x_weight": xerr.bit_count(),
        "true_z_weight": zerr.bit_count(),
        "measured_syndrome_z": list(target_z),
        "measured_syndrome_x": list(target_x),
        "x_decoder": cx, "z_decoder": cz,
        "x_residual_sites": sites(residual_x, model.n),
        "z_residual_sites": sites(residual_z, model.n),
        "remaining_z_check_weight": sx_left,
        "remaining_x_check_weight": sz_left,
        "syndrome_consistent": consistent,
        "logical_x": lx, "logical_z": lz, "logical_failure": logical,
        "outcome": outcome,
        "pauli_frame_failure": outcome != "STABILIZER_EQUIVALENT_SUCCESS",
    }
