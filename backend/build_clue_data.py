import collections
import json
import os
import unicodedata


ROOT = os.path.dirname(__file__)
DATA = os.path.join(ROOT, "data")
MIN_LENGTH = 2
MAX_LENGTH = 13

# Soglie di rango (posizione nella classifica di frequenza, 0 = piu' comune)
# per assegnare ogni parola a un livello di difficolta'.
TIER_THRESHOLDS = [
    (800, "facilissima"),
    (3000, "facile"),
    (12000, "media"),
    (50000, "alta"),
]
DEFAULT_TIER = "altissima"  # parole non presenti nella lista di frequenza


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


def load_frequency_ranks(path: str) -> dict:
    """word -> rank (0 = most frequent), first occurrence wins."""
    ranks = {}
    if not os.path.exists(path):
        return ranks
    with open(path, encoding="utf-8", errors="ignore") as file:
        for i, line in enumerate(file):
            parts = line.split()
            if not parts:
                continue
            word = normalize_word(parts[0])
            if word and word not in ranks:
                ranks[word] = i
    return ranks


def tier_for_rank(rank) -> str:
    if rank is None:
        return DEFAULT_TIER
    for threshold, tier in TIER_THRESHOLDS:
        if rank < threshold:
            return tier
    return DEFAULT_TIER


def main():
    source_definitions = os.path.join(DATA, "italian_synsets_compact.json")
    source_words = os.path.join(DATA, "parole_it.txt")
    source_freq = os.path.join(DATA, "it_50k.txt")
    output_words = os.path.join(DATA, "words_by_len.json")
    output_clues = os.path.join(DATA, "clues_by_word.json")
    output_difficulty = os.path.join(DATA, "word_difficulty.json")

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
            if word:
                allowed_words.add(word)

    by_length = collections.defaultdict(list)
    for word in sorted(allowed_words):
        by_length[len(word)].append(word)

    with open(output_words, "w", encoding="utf-8") as file:
        json.dump({str(k): v for k, v in sorted(by_length.items())}, file, ensure_ascii=False)

    with open(output_clues, "w", encoding="utf-8") as file:
        json.dump(
            {word: clues[word] for word in sorted(allowed_words) if word in clues},
            file,
            ensure_ascii=False,
        )

    ranks = load_frequency_ranks(source_freq)
    difficulty = {word: tier_for_rank(ranks.get(word)) for word in sorted(allowed_words)}
    with open(output_difficulty, "w", encoding="utf-8") as file:
        json.dump(difficulty, file, ensure_ascii=False)

    tier_counts = collections.Counter(difficulty.values())

    print("Parole con definizione:", len(allowed_words))
    for length, words in sorted(by_length.items()):
        print(length, len(words))
    print("Livelli di difficolta':")
    for _, tier in TIER_THRESHOLDS + [(None, DEFAULT_TIER)]:
        print(" ", tier, tier_counts.get(tier, 0))
    print("Creati:", output_words)
    print("Creati:", output_clues)
    print("Creati:", output_difficulty)


if __name__ == "__main__":
    main()