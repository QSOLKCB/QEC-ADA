#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Independent stdlib finite-graph and classical BP reference primitives.

No QEC donor decoder is imported. The channel and min-sum BP implementation
are a controlled *classical GF(2)* experiment, not the native GF(3) decoder,
a hardware-QEC benchmark or a reproduction of QEC's whole BP implementation.
"""
from __future__ import annotations

from collections import defaultdict
import hashlib
import itertools
import math


MAX_VARIABLES = 128
MAX_CHECKS = 128
MAX_EDGES = 2048
HEADER = "QECADA-TANNER-EDGES-V1"


def digest_int(*fields: object) -> int:
    data = "|".join(str(v) for v in fields).encode("utf-8")
    return int.from_bytes(hashlib.sha256(data).digest()[:8], "big")


def canonical_graph(n: int, m: int, edges: list[tuple[int, int]]) -> bytes:
    if (type(n) is not int or type(m) is not int
            or not 1 <= n <= MAX_VARIABLES
            or not 1 <= m <= MAX_CHECKS
            or type(edges) is not list or len(edges) > MAX_EDGES
            or any(type(c) is not int or type(v) is not int or
                   not (1 <= c <= m and 1 <= v <= n) for c, v in edges)
            or sorted(set(edges)) != edges):
        raise ValueError("invalid or noncanonical sparse graph")
    lines = [HEADER, f"variables={n}", f"checks={m}",
             f"edges={len(edges)}"]
    lines += [f"{c},{v}" for c, v in edges]
    return ("\n".join(lines) + "\n").encode("ascii")


def generated_graph(graph_id: int, n: int, m: int, seed: str
                    ) -> list[tuple[int, int]]:
    if (type(graph_id) is not int or graph_id < 0 or not isinstance(seed, str)
            or not seed or not 16 <= n <= MAX_VARIABLES
            or not 8 <= m <= MAX_CHECKS):
        raise ValueError("invalid deterministic graph configuration")

    support: set[tuple[int, int]] = set()
    for v in range(1, n + 1):
        selected = set()
        for lane in range(3):
            c = digest_int("variable", seed, graph_id, v, lane) % m + 1
            while c in selected:
                c = c % m + 1
            selected.add(c)
            support.add((c, v))

    for c in range(1, m + 1):
        selected = {v for check, v in support if check == c}
        requested = 4 + (c + graph_id) % 3
        lane = 0
        while len(selected) < requested:
            v = digest_int("check", seed, graph_id, c, lane) % n + 1
            while v in selected:
                v = v % n + 1
            selected.add(v)
            support.add((c, v))
            lane += 1

    # All four graph families share the same n,m and noise schedule.
    # Different fixed topology interventions are observational only.
    family = graph_id % 4
    a = min(7, n)
    b = min(5, m)
    if family in (1, 3):
        support.update((c, v) for c in range(1, b + 1)
                       for v in range(1, a + 1))
    if family in (2, 3):
        support.update((c, v) for c in range(m - b + 1, m + 1)
                       for v in range(n - a + 1, n + 1))
    if family == 0:
        support.update((c, (c % n) + 1)
                       for c in range(1, m + 1))
    if len(support) > MAX_EDGES:
        raise ValueError("generated graph exceeds native edge capacity")
    edges = sorted(support)
    canonical_graph(n, m, edges)
    return edges


def directed_adjacency(n: int, m: int, edges: list[tuple[int, int]]):
    directed = []
    for c, v in edges:
        directed.append((v, n + c))
        directed.append((n + c, v))
    outgoing = defaultdict(list)
    for i, (source, _) in enumerate(directed):
        outgoing[source].append(i)
    neighbours = [[] for _ in directed]
    backward = [[] for _ in directed]
    for i, (source, target) in enumerate(directed):
        for j in outgoing[target]:
            if directed[j][1] != source:
                neighbours[i].append(j)
                backward[j].append(i)
    return directed, neighbours, backward


def reference_scc(neighbours: list[list[int]],
                  backward: list[list[int]]) -> list[list[int]]:
    """Iterative Kosaraju reference, independent of native Ada data layout."""
    count = len(neighbours)
    visited = [False] * count
    finish = []
    for root in range(count):
        if visited[root]:
            continue
        visited[root] = True
        stack = [(root, 0)]
        while stack:
            node, cursor = stack[-1]
            if cursor == len(neighbours[node]):
                finish.append(node)
                stack.pop()
                continue
            stack[-1] = (node, cursor + 1)
            target = neighbours[node][cursor]
            if not visited[target]:
                visited[target] = True
                stack.append((target, 0))

    assigned = set()
    groups = []
    for root in reversed(finish):
        if root in assigned:
            continue
        group = []
        stack = [root]
        assigned.add(root)
        while stack:
            node = stack.pop()
            group.append(node)
            for prev in backward[node]:
                if prev not in assigned:
                    assigned.add(prev)
                    stack.append(prev)
        groups.append(sorted(group))
    return groups


def perron_reference(neighbours: list[list[int]],
                     group: list[int], limit: int = 3000) -> dict:
    """Separate Python eigenvalue iteration, not a production dependency."""
    members = set(group)
    v = {node: 1.0 / len(group) for node in group}
    for step in range(1, limit + 1):
        sums = {node: math.fsum(v[j] for j in neighbours[node]
                                if j in members)
                for node in group}
        ratios = [sums[node] / v[node] for node in group]
        lower, upper = min(ratios), max(ratios)
        if upper - lower <= 1e-10 * max(1.0, upper):
            rho = (lower + upper) / 2.0
            norm = math.fsum(v[node] ** 2 for node in group)
            energies = {node: v[node] ** 2 / norm for node in group}
            return {
                "rho": rho,
                "ipr": math.fsum(value**2 for value in energies.values()),
                "energies": energies,
                "iterations": step,
            }
        updated = {node: v[node] + sums[node] for node in group}
        norm = math.fsum(updated.values())
        v = {node: updated[node] / norm for node in group}
    raise ValueError("independent SCC Perron reference did not converge")


def reference_spectrum(n: int, m: int, edges: list[tuple[int, int]]) -> dict:
    canonical_graph(n, m, edges)
    directed, outgoing, backward = directed_adjacency(n, m, edges)
    blocks = reference_scc(outgoing, backward)
    cyclic = [block for block in blocks if len(block) > 1]
    if not cyclic:
        return {"status": "NO_EDGES" if not edges else "ACYCLIC",
                "spectral_radius": 0.0, "ipr": 0.0,
                "eeec": 0.0, "root": 0, "ties": 0, "mode_edges": 0,
                "scc_count": len(blocks), "cyclic_scc_count": 0,
                "mode_energy": {}}
    analyses = [(min(block), block, perron_reference(outgoing, block))
                for block in cyclic]
    max_rho = max(item[2]["rho"] for item in analyses)
    tied = [item for item in analyses
            if abs(item[2]["rho"] - max_rho) <= 1e-8]
    root, members, mode = min(tied, key=lambda item: item[0])
    energies = mode["energies"]
    ranking = sorted(energies, key=lambda i: (-energies[i], i))
    top = math.isqrt(len(members))
    if top * top < len(members):
        top += 1
    return {
        "status": "CONVERGED_NUMERIC", "spectral_radius": mode["rho"],
        "ipr": mode["ipr"],
        "eeec": math.fsum(energies[i] for i in ranking[:top]),
        "root": root + 1, "ties": len(tied),
        "mode_edges": len(members),
        "scc_count": len(blocks), "cyclic_scc_count": len(cyclic),
        "mode_energy": {node + 1: value for node, value in energies.items()},
    }


def _clip(v: int) -> int:
    return max(-64, min(64, v))


def decode_min_sum(n: int, m: int, edges: list[tuple[int, int]],
                   error_sites: frozenset[int], max_rounds: int = 18
                   ) -> dict:
    """Actual deterministic integer min-sum BP over classical GF(2) H.

    All-zero codeword transmitted; BSC errors form the received vector.
    Failed frame iff output differs from known transmitted codeword, even
    when parity happens to be satisfied (undetected wrong codeword).
    """
    canonical_graph(n, m, edges)
    if not 1 <= max_rounds <= 100 or any(
            type(v) is not int or not 1 <= v <= n for v in error_sites):
        raise ValueError("invalid controlled BP inputs")

    checks = [[] for _ in range(m + 1)]
    variables = [[] for _ in range(n + 1)]
    for c, v in edges:
        checks[c].append(v)
        variables[v].append(c)
    received = [0] + [int(v in error_sites) for v in range(1, n + 1)]
    prior = [0] + [(-6 if received[v] else 6) for v in range(1, n + 1)]
    v_to_c = {(c, v): prior[v] for c, v in edges}

    def syndrome(bits: list[int]) -> int:
        return sum(sum(bits[v] for v in checks[c]) % 2
                   for c in range(1, m + 1))

    previous = received
    trace = [{"round": 0, "syndrome_weight": syndrome(received),
              "decision_hamming": 0, "estimated_errors": sum(received[1:])}]
    final_bits = received
    converged = trace[-1]["syndrome_weight"] == 0
    for cycle in range(1, max_rounds + 1):
        if converged:
            break
        c_to_v = {}
        for c in range(1, m + 1):
            sites = checks[c]
            for v in sites:
                others = [v_to_c[(c, u)] for u in sites if u != v]
                if not others:
                    value = 64             # degree-one even-parity constraint
                else:
                    magnitude = min(abs(x) for x in others)
                    negative = sum(x < 0 for x in others) % 2
                    value = -magnitude if negative else magnitude
                c_to_v[(c, v)] = _clip(value)

        posterior = [0] + [
            prior[v] + sum(c_to_v[(c, v)] for c in variables[v])
            for v in range(1, n + 1)
        ]
        final_bits = [0] + [int(posterior[v] < 0)
                            for v in range(1, n + 1)]
        weight = syndrome(final_bits)
        trace.append({
            "round": cycle, "syndrome_weight": weight,
            "decision_hamming": sum(final_bits[v] != previous[v]
                                    for v in range(1, n + 1)),
            "estimated_errors": sum(final_bits[1:]),
        })
        converged = weight == 0
        if converged:
            break
        v_to_c = {
            (c, v): _clip(posterior[v] - c_to_v[(c, v)])
            for c, v in edges
        }
        previous = final_bits

    frame_failure = any(final_bits[1:])
    return {
        "error_weight": len(error_sites),
        "initial_syndrome_weight": trace[0]["syndrome_weight"],
        "iterations": len(trace) - 1,
        "checks_satisfied": converged,
        "frame_failure": frame_failure,
        "undetected_failure": frame_failure and converged,
        "final_error_weight": sum(final_bits[1:]),
        "trace": trace,
    }


def deterministic_noise(seed: str, graph_id: int, noise_bps: int,
                        trial: int, n: int) -> frozenset[int]:
    if (type(noise_bps) is not int or not 0 <= noise_bps <= 5000
            or type(trial) is not int or trial < 0):
        raise ValueError("invalid deterministic BSC parameters")
    return frozenset(
        v for v in range(1, n + 1)
        if digest_int("channel", seed, graph_id, noise_bps, trial, v)
        % 10_000 < noise_bps
    )


def auroc(pairs: list[tuple[float, bool]]) -> float | None:
    positives = sum(bool(y) for _, y in pairs)
    negatives = len(pairs) - positives
    if positives == 0 or negatives == 0:
        return None
    sorted_pairs = sorted(pairs, key=lambda pair: pair[0])
    lower_negative = 0
    favourable = 0.0
    for _, group in itertools.groupby(sorted_pairs, key=lambda pair: pair[0]):
        values = list(group)
        pos = sum(y for _, y in values)
        neg = len(values) - pos
        favourable += pos * lower_negative + 0.5 * pos * neg
        lower_negative += neg
    return favourable / (positives * negatives)


def average_precision(pairs: list[tuple[float, bool]]) -> float | None:
    positives = sum(bool(y) for _, y in pairs)
    if positives == 0:
        return None
    cumulative_pos = 0
    cumulative_count = 0
    result = 0.0
    for _, group in itertools.groupby(
            sorted(pairs, key=lambda pair: -pair[0]),
            key=lambda pair: pair[0]):
        values = list(group)
        hits = sum(y for _, y in values)
        cumulative_pos += hits
        cumulative_count += len(values)
        result += (hits / positives) * (cumulative_pos / cumulative_count)
    return result


def confusion(pairs: list[tuple[float, bool]],
              threshold: float) -> dict[str, int | float | None]:
    tp = fp = tn = fn = 0
    for score, actual in pairs:
        guessed = score >= threshold
        if guessed and actual:
            tp += 1
        elif guessed:
            fp += 1
        elif actual:
            fn += 1
        else:
            tn += 1
    p = tp + fn
    n = tn + fp
    tpr = tp / p if p else None
    tnr = tn / n if n else None
    return {
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "balanced_accuracy": (tpr + tnr) / 2
          if tpr is not None and tnr is not None else None,
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tpr,
    }


def fit_threshold(training: list[tuple[float, bool]]) -> float | None:
    if not training or auroc(training) is None:
        return None
    # Training data only, conservative highest-threshold tie policy.
    candidates = sorted({score for score, _ in training})
    candidates.append(candidates[-1] + 1.0)
    selected = max(
        candidates,
        key=lambda t: (confusion(training, t)["balanced_accuracy"], t),
    )
    return selected


def _average_ranks(values: list[float]) -> list[float]:
    result = [0.0] * len(values)
    order = sorted(range(len(values)), key=lambda k: values[k])
    for _, group in itertools.groupby(
            enumerate(order), key=lambda pair: values[pair[1]]):
        indices = [index for index, _ in group]
        rank = (indices[0] + indices[-1]) / 2 + 1
        for index in indices:
            result[order[index]] = rank
    return result


def spearman(x: list[float], y: list[float]) -> float | None:
    if len(x) != len(y) or len(x) < 3:
        return None
    a, b = _average_ranks(x), _average_ranks(y)
    am, bm = math.fsum(a)/len(a), math.fsum(b)/len(b)
    numerator = math.fsum((u-am)*(v-bm) for u, v in zip(a,b))
    xx = math.fsum((u-am)**2 for u in a)
    yy = math.fsum((v-bm)**2 for v in b)
    return numerator / math.sqrt(xx*yy) if xx > 0 and yy > 0 else None
