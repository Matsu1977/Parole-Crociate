import collections
import json
import os
import unicodedata


ROOT = os.path.dirname(__file__)
DATA = os.path.join(ROOT, "data")
MIN_LENGTH = 3
MAX_LENGTH = 13


def normalize_word(raw: str) -> str:
    """Return an uppercase grid word, or an empty string when unsuitable."""
    raw = raw.strip()
    if not raw:
        return ""

    letters = []
    for char in unicodedata.normalize("NFD", raw):
        if unicodedata.category(char) == "Mn":
            continue
        char = char.upper()
        if not ("A" <= char <= "Z"):
            return ""
        letters.append(char)

    word = "".join(letters)
    return word if MIN_LENGTH <= len(word) <= MAX_LENGTH else ""


def letters_only(text: str) -> str:
    return "".join(
        char.upper()
        for char in unicodedata.normalize("NFD", text)
        if "A" <= char.upper() <= "Z"
    )


def choose_definition(entries, answer: str) -> str:
    """Choose the first concise Italian definition that does not reveal the answer."""
    answer_letters = letters_only(answer)
    for entry in entries:
        definition = " ".join(str(entry.get("definition_it") or "").split())
        if not 12 <= len(definition) <= 220:
            continue
        if answer_letters in letters_only(definition):
            continue
        return definition[0].upper() + definition[1:]
    return ""


def main():
    source_definitions = os.path.join(DATA, "italian_synsets_compact.json")
    source_words = os.path.join(DATA, "parole_it.txt")
    output_words = os.path.join(DATA, "words_by_len.json")
    output_clues = os.path.join(DATA, "clues_by_word.json")

    with open(source_definitions, encoding="utf-8") as file:
        raw_definitions = json.load(file)

    clues = {}
    for raw_word, entries in raw_definitions.items():
        word = normalize_word(raw_word)
        if not word or not isinstance(entries, list):
            continue
        clue = choose_definition(entries, word)
        if clue:
            clues[word] = clue

    allowed_words = set()
    with open(source_words, encoding="utf-8", errors="ignore") as file:
        for line in file:
            word = normalize_word(line)
            if word and word in clues:
                allowed_words.add(word)

    by_length = collections.defaultdict(list)
    for word in sorted(allowed_words):
        by_length[len(word)].append(word)

    with open(output_words, "w", encoding="utf-8") as file:
        json.dump({str(k): v for k, v in sorted(by_length.items())}, file, ensure_ascii=False)

    with open(output_clues, "w", encoding="utf-8") as file:
        json.dump(
            {word: clues[word] for word in sorted(allowed_words)},
            file,
            ensure_ascii=False,
        )

    print("Parole con definizione:", len(allowed_words))
    for length, words in sorted(by_length.items()):
        print(length, len(words))
    print("Creati:", output_words)
    print("Creati:", output_clues)


if __name__ == "__main__":
    main()
