import collections
import json
import os
import unicodedata

ROOT = os.path.dirname(__file__)
MIN_LENGTH = 3
MAX_LENGTH = 13


def normalize_word(raw: str) -> str:
    """Return a simple Italian grid word, or an empty string if it is unsuitable."""
    raw = raw.strip()
    if not raw:
        return ""

    # Reject punctuation and separators instead of silently joining fragments:
    # l'amico and porta-aerei must not become LAMICO and PORTAAEREI.
    decomposed = unicodedata.normalize("NFD", raw)
    letters = []
    for char in decomposed:
        if unicodedata.category(char) == "Mn":
            continue
        upper = char.upper()
        if not ("A" <= upper <= "Z"):
            return ""
        letters.append(upper)

    word = "".join(letters)
    if not MIN_LENGTH <= len(word) <= MAX_LENGTH:
        return ""
    return word


def main():
    seen = set()
    by_length = collections.defaultdict(list)
    source = os.path.join(ROOT, "data", "parole_it.txt")
    destination = os.path.join(ROOT, "data", "words_by_len.json")

    with open(source, encoding="utf-8", errors="ignore") as file:
        for line in file:
            word = normalize_word(line)
            if word and word not in seen:
                seen.add(word)
                by_length[len(word)].append(word)

    output = {str(length): sorted(words) for length, words in sorted(by_length.items())}
    with open(destination, "w", encoding="utf-8") as file:
        json.dump(output, file, ensure_ascii=False)

    print("Parole valide:", sum(len(words) for words in by_length.values()))
    for length, words in sorted(by_length.items()):
        print(length, len(words))


if __name__ == "__main__":
    main()
    