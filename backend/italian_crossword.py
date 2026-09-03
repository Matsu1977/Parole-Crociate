import json
import os
import random
import time

ROOT = os.path.dirname(__file__)

_WORDS = None   # {L: [word,...]}
_MASK = None    # {L: {(pos,ch): int_bitmask}}
_FULL = None    # {L: int full mask}
_CAP = 200000
_DIFFICULTY = None  # {word: tier}
_TIER_ORDER = ["facilissima", "facile", "media", "alta", "altissima"]
_TIER_CACHE = {}  # difficulty -> (words_by_len, mask_by_len, full_by_len)

try:
    _popcount = int.bit_count
except AttributeError:  # py<3.10
    def _popcount(x):
        return bin(x).count("1")


def _load() -> None:
    global _WORDS, _MASK, _FULL, _DIFFICULTY
    if _WORDS is not None:
        return
    with open(os.path.join(ROOT, "data", "words_by_len.json")) as f:
        raw = json.load(f)
    _WORDS, _MASK, _FULL = {}, {}, {}
    for k, lst in raw.items():
        L = int(k)
        if len(lst) > _CAP:
            lst = random.sample(lst, _CAP)
        _WORDS[L] = lst
        _FULL[L] = (1 << len(lst)) - 1
        m = {}
        for i, w in enumerate(lst):
            bit = 1 << i
            for pos, ch in enumerate(w):
                key = (pos, ch)
                m[key] = m.get(key, 0) | bit
        _MASK[L] = m

    diff_path = os.path.join(ROOT, "data", "word_difficulty.json")
    if os.path.exists(diff_path):
        with open(diff_path, encoding="utf-8") as f:
            _DIFFICULTY = json.load(f)
    else:
        _DIFFICULTY = {}


def _pool_for_difficulty(difficulty: str):
    """Return (words_by_len, mask_by_len, full_by_len) restricted to words whose
    tier is at or below the requested difficulty (cumulative: 'facile' includes
    'facilissima' too, so the pool stays large enough to actually fill a grid)."""
    if difficulty not in _TIER_ORDER:
        difficulty = "alta"
    if difficulty == "altissima" or not _DIFFICULTY:
        return _WORDS, _MASK, _FULL
    if difficulty in _TIER_CACHE:
        return _TIER_CACHE[difficulty]

    tier_idx = _TIER_ORDER.index(difficulty)
    allowed_tiers = set(_TIER_ORDER[: tier_idx + 1])

    words_by_len, mask_by_len, full_by_len = {}, {}, {}
    for L, lst in _WORDS.items():
        filtered = [w for w in lst if _DIFFICULTY.get(w, "altissima") in allowed_tiers]
        if not filtered:
            continue
        words_by_len[L] = filtered
        full_by_len[L] = (1 << len(filtered)) - 1
        m = {}
        for i, w in enumerate(filtered):
            bit = 1 << i
            for pos, ch in enumerate(w):
                key = (pos, ch)
                m[key] = m.get(key, 0) | bit
        mask_by_len[L] = m

    result = (words_by_len, mask_by_len, full_by_len)
    _TIER_CACHE[difficulty] = result
    return result


def _runs_ok(R: int, C: int, blocked: set, min_run: int = 3, max_run: int = 13) -> bool:
    def check(cells):
        run = 0
        for cell in cells:
            if cell in blocked:
                if 0 < run < min_run:
                    return False
                run = 0
            else:
                run += 1
                if run > max_run:
                    return False
        if 0 < run < min_run:
            return False
        return True

    for r in range(R):
        if not check([(r, c) for c in range(C)]):
            return False
    for c in range(C):
        if not check([(r, c) for r in range(R)]):
            return False
    return True


def _connected(R: int, C: int, blocked: set) -> bool:
    whites = [(r, c) for r in range(R) for c in range(C) if (r, c) not in blocked]
    if not whites:
        return False
    seen = {whites[0]}
    stack = [whites[0]]
    while stack:
        r, c = stack.pop()
        for dr, dc in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < R and 0 <= nc < C and (nr, nc) not in blocked and (nr, nc) not in seen:
                seen.add((nr, nc))
                stack.append((nr, nc))
    return len(seen) == len(whites)


def _short_ok(R, C, blocked, min_run):
    def check(cells):
        run = 0
        for cell in cells:
            if cell in blocked:
                if 0 < run < min_run:
                    return False
                run = 0
            else:
                run += 1
        return not (0 < run < min_run)
    for r in range(R):
        if not check([(r, c) for c in range(C)]):
            return False
    for c in range(C):
        if not check([(r, c) for r in range(R)]):
            return False
    return True


def _long_runs(R, C, blocked, max_run):
    runs = []
    for r in range(R):
        cur = []
        for c in range(C):
            if (r, c) in blocked:
                if len(cur) > max_run:
                    runs.append(cur)
                cur = []
            else:
                cur.append((r, c))
        if len(cur) > max_run:
            runs.append(cur)
    for c in range(C):
        cur = []
        for r in range(R):
            if (r, c) in blocked:
                if len(cur) > max_run:
                    runs.append(cur)
                cur = []
            else:
                cur.append((r, c))
        if len(cur) > max_run:
            runs.append(cur)
    return runs


def gen_pattern(R: int, C: int, density: float = 0.12, min_run: int = 4, max_run: int = 9, restarts: int = 3000) -> set | None:
    for _ in range(restarts):
        blocked = set()
        ok = True
        for _ in range(400):
            longs = _long_runs(R, C, blocked, max_run)
            if not longs:
                break
            run = random.choice(longs)
            L = len(run)
            cands = list(range(min_run, L - min_run + 1))
            random.shuffle(cands)
            placed = False
            for p in cands:
                cell = run[p]
                sym = (R - 1 - cell[0], C - 1 - cell[1])
                if cell in blocked or sym in blocked:
                    continue
                trial = blocked | {cell, sym}
                if _short_ok(R, C, trial, min_run):
                    blocked = trial
                    placed = True
                    break
            if not placed:
                ok = False
                break
        else:
            ok = False
        if ok and _runs_ok(R, C, blocked, min_run=min_run, max_run=max_run) and _connected(R, C, blocked):
            return blocked
    return None


def get_slots(R: int, C: int, blocked: set) -> list:
    slots = []
    for r in range(R):
        c = 0
        while c < C:
            if (r, c) in blocked:
                c += 1
                continue
            start = c
            while c < C and (r, c) not in blocked:
                c += 1
            if c - start >= 2:
                slots.append({"cells": [(r, start + i) for i in range(c - start)], "dir": "across", "len": c - start})
    for c in range(C):
        r = 0
        while r < R:
            if (r, c) in blocked:
                r += 1
                continue
            start = r
            while r < R and (r, c) not in blocked:
                r += 1
            if r - start >= 2:
                slots.append({"cells": [(start + i, c) for i in range(r - start)], "dir": "down", "len": r - start})
    return slots


def _bits(x):
    while x:
        b = x & -x
        yield b.bit_length() - 1
        x ^= b


_ALPHA = [chr(c) for c in range(65, 91)]


def _attempt(slots, neighbors, lens, masks, node_limit, words_by_len=None, full_by_len=None):
    words_by_len = words_by_len if words_by_len is not None else _WORDS
    full_by_len = full_by_len if full_by_len is not None else _FULL
    n = len(slots)
    domains = [full_by_len[L] for L in lens]
    filled = {}
    used = set()
    nodes = [0]

    def bt():
        nodes[0] += 1
        if nodes[0] > node_limit:
            return "cap"
        best = -1
        bestn = None
        for i in range(n):
            if i in filled:
                continue
            d = domains[i]
            if d == 0:
                return False
            m = _popcount(d)
            if bestn is None or m < bestn:
                bestn = m
                best = i
                if m == 1:
                    break
        if best == -1:
            return True
        words = words_by_len[lens[best]]
        ids = list(_bits(domains[best]))
        random.shuffle(ids)
        nb = neighbors[best]
        for cid in ids:
            w = words[cid]
            if w in used:
                continue
            trail = []
            ok = True
            for pos_i, j, pos_j in nb:
                if j in filled:
                    continue
                mask = masks[j].get((pos_j, w[pos_i]), 0)
                nd = domains[j] & mask
                trail.append((j, domains[j]))
                domains[j] = nd
                if nd == 0:
                    ok = False
                    break
            if ok:
                filled[best] = w
                used.add(w)
                r = bt()
                if r is True:
                    return True
                if r == "cap":
                    for j, old in trail:
                        domains[j] = old
                    return "cap"
                del filled[best]
                used.discard(w)
            for j, old in trail:
                domains[j] = old
        return False

    r = bt()
    return dict(filled) if r is True else None


def solve(slots: list, time_budget: float = 6.0, words_by_len=None, mask_by_len=None, full_by_len=None) -> dict | None:
    words_by_len = words_by_len if words_by_len is not None else _WORDS
    mask_by_len = mask_by_len if mask_by_len is not None else _MASK
    full_by_len = full_by_len if full_by_len is not None else _FULL
    across_at, down_at = {}, {}
    for i, s in enumerate(slots):
        store = across_at if s["dir"] == "across" else down_at
        for pos, cell in enumerate(s["cells"]):
            store[cell] = (i, pos)
    neighbors = []
    for i, s in enumerate(slots):
        perp = down_at if s["dir"] == "across" else across_at
        neighbors.append([(pos_i, *perp[cell]) for pos_i, cell in enumerate(s["cells"]) if cell in perp])
    lens = [s["len"] for s in slots]
    masks = [mask_by_len[L] for L in lens]

    deadline = time.time() + time_budget
    node_limit = 6000
    while time.time() < deadline:
        res = _attempt(slots, neighbors, lens, masks, node_limit, words_by_len, full_by_len)
        if res is not None:
            return res
    return None


def _assemble(R, C, blocked, slots, filled):
    number_at = {}
    num = 1
    for r in range(R):
        for c in range(C):
            if (r, c) in blocked:
                continue
            sa = (c == 0 or (r, c - 1) in blocked) and (c + 1 < C and (r, c + 1) not in blocked)
            sd = (r == 0 or (r - 1, c) in blocked) and (r + 1 < R and (r + 1, c) not in blocked)
            if sa or sd:
                number_at[(r, c)] = num
                num += 1

    grid = {}
    for i, word in filled.items():
        for (r, c), ch in zip(slots[i]["cells"], word):
            grid[(r, c)] = ch

    across, down = [], []
    for i, word in filled.items():
        s = slots[i]
        r, c = s["cells"][0]
        entry = {"num": number_at.get((r, c)), "answer": word, "row": r, "col": c,
                 "length": s["len"], "direction": s["dir"], "clue": ""}
        (across if s["dir"] == "across" else down).append(entry)
    across.sort(key=lambda x: x["num"])
    down.sort(key=lambda x: x["num"])

    cells = []
    solution = {}
    for (r, c), ch in sorted(grid.items()):
        cell = {"row": r, "col": c}
        if (r, c) in number_at:
            cell["number"] = number_at[(r, c)]
        cells.append(cell)
        solution[f"{r}-{c}"] = ch

    return {"rows": R, "cols": C, "cells": cells, "across": across, "down": down, "solution": solution}


_GRID_SIZE_BY_DIFFICULTY = {
    "facilissima": 9,
    "facile": 11,
    "media": 13,
    "alta": 13,
    "altissima": 13,
}


def build_italian_crossword(R: int = None, C: int = None, total_budget: float = 90.0, per_solve: float = 3.0, min_run: int = 3, max_run: int = 8, difficulty: str = "alta") -> dict | None:
    _load()
    size = _GRID_SIZE_BY_DIFFICULTY.get(difficulty, 13)
    R = R or size
    C = C or size
    words_by_len, mask_by_len, full_by_len = _pool_for_difficulty(difficulty)
    deadline = time.time() + total_budget
    while time.time() < deadline:
        blocked = gen_pattern(R, C, min_run=min_run, max_run=max_run)
        if not blocked:
            continue
        slots = get_slots(R, C, blocked)
        if any(s["len"] not in words_by_len for s in slots):
            continue
        filled = solve(
            slots,
            time_budget=min(per_solve, deadline - time.time()),
            words_by_len=words_by_len,
            mask_by_len=mask_by_len,
            full_by_len=full_by_len,
        )
        if filled is not None:
            return _assemble(R, C, blocked, slots, filled)
    return None


if __name__ == "__main__":
    import sys
    R = int(sys.argv[1]) if len(sys.argv) > 1 else 13
    C = int(sys.argv[2]) if len(sys.argv) > 2 else 13
    _load()
    t = time.time()
    p = build_italian_crossword(R, C, total_budget=40)
    dt = time.time() - t
    if p:
        print(f"{R}x{C} OK in {dt:.2f}s words={len(p['across'])+len(p['down'])}")
    else:
        print(f"{R}x{C} FAILED in {dt:.2f}s")