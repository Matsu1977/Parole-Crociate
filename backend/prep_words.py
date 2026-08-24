import unicodedata
import json
import collections
import os

ROOT = os.path.dirname(__file__)


def norm(w):
    w = w.strip().upper()
    w = "".join(c for c in unicodedata.normalize("NFD", w) if unicodedata.category(c) != "Mn")
    return "".join(c for c in w if "A" <= c <= "Z")


def main():
    seen = set()
    by = collections.defaultdict(list)
    with open(os.path.join(ROOT, "data", "parole_it.txt"), encoding="utf-8", errors="ignore") as f:
        for line in f:
            w = norm(line)
            if 2 <= len(w) <= 13 and w not in seen:
                seen.add(w)
                by[len(w)].append(w)
    out = {str(k): v for k, v in by.items()}
    with open(os.path.join(ROOT, "data", "words_by_len.json"), "w") as f:
        json.dump(out, f)
    print("total", sum(len(v) for v in by.values()))
    for L in sorted(by):
        print(L, len(by[L]))


if __name__ == "__main__":
    main()
