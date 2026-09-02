import unicodedata
import random
import json
import os

# High-difficulty Italian fallback word pool (word + elegant/hard clue)
FALLBACK_POOL = [
    {"word": "ABULIA", "clue": "Grave mancanza di volontà"},
    {"word": "CAVILLO", "clue": "Sottigliezza usata per contestare senza fondamento"},
    {"word": "EPESEGESI", "clue": "Aggiunta esplicativa in retorica"},
    {"word": "LAPIDARIO", "clue": "Conciso ed essenziale, come un'iscrizione"},
    {"word": "MEANDRO", "clue": "Ansa sinuosa di un corso d'acqua"},
    {"word": "OBLIO", "clue": "La caduta nel dimenticatoio"},
    {"word": "PLETORA", "clue": "Sovrabbondanza eccessiva"},
    {"word": "RECONDITO", "clue": "Nascosto, difficile da penetrare"},
    {"word": "SIBILLINO", "clue": "Oscuro e ambiguo come un oracolo"},
    {"word": "TACITURNO", "clue": "Chi parla assai di rado"},
    {"word": "UBIQUO", "clue": "Presente ovunque nello stesso istante"},
    {"word": "VELLEITA", "clue": "Aspirazione priva di reale volontà"},
    {"word": "ATAVICO", "clue": "Che risale a origini remotissime"},
    {"word": "CRISALIDE", "clue": "Stadio intermedio prima della farfalla"},
    {"word": "DEDALO", "clue": "Intrico labirintico di vie"},
    {"word": "EFFIMERO", "clue": "Che dura lo spazio di un giorno"},
    {"word": "FATUO", "clue": "Vano e privo di sostanza"},
    {"word": "GARRULO", "clue": "Che cinguetta o chiacchiera senza sosta"},
    {"word": "IROSO", "clue": "Facile all'ira, collerico"},
    {"word": "LUMINARE", "clue": "Massimo esperto in una disciplina"},
    {"word": "NEFANDO", "clue": "Talmente empio da non potersi nominare"},
    {"word": "OSTRACISMO", "clue": "Esclusione decretata dalla comunità"},
    {"word": "PROBO", "clue": "Di specchiata onestà"},
    {"word": "RATTO", "clue": "Rapimento, oppure assai veloce"},
    {"word": "SAGACE", "clue": "Dotato di acuto intuito"},
    {"word": "TERGO", "clue": "La parte posteriore, il retro"},
    {"word": "UGGIOSO", "clue": "Fastidiosamente noioso e grigio"},
    {"word": "VETUSTO", "clue": "Antichissimo e venerando"},
    {"word": "ALACRE", "clue": "Pronto e pieno di operoso vigore"},
    {"word": "BIECO", "clue": "Sguardo torvo e malevolo"},
    {"word": "COTURNO", "clue": "Alta calzatura degli attori tragici antichi"},
    {"word": "DIAFANO", "clue": "Trasparente, quasi immateriale"},
    {"word": "ESIZIALE", "clue": "Foriero di rovina e morte"},
    {"word": "FRUGALE", "clue": "Sobrio e parco nel vitto"},
    {"word": "GNOMICO", "clue": "Sentenzioso, che esprime massime"},
    {"word": "IERATICO", "clue": "Solenne e sacrale nell'atteggiamento"},
    {"word": "LEZIOSO", "clue": "Affettato con smorfie ricercate"},
    {"word": "MEFITICO", "clue": "Dall'esalazione pestilenziale"},
    {"word": "PARCO", "clue": "Moderato, che spende con misura"},
    {"word": "REMORA", "clue": "Indugio, esitazione che trattiene"},
    {"word": "SPECIOSO", "clue": "Apparentemente valido ma ingannevole"},
    {"word": "TRUCE", "clue": "Feroce e minaccioso nell'aspetto"},
    {"word": "VACUO", "clue": "Vuoto di contenuto e significato"},
    {"word": "ZELANTE", "clue": "Solerte fino allo scrupolo"},
    {"word": "ACRIMONIA", "clue": "Astio pungente e rancoroso"},
    {"word": "BLANDO", "clue": "Lieve, poco intenso"},
    {"word": "CADUCO", "clue": "Destinato a durare assai poco"},
    {"word": "DIROCCATO", "clue": "Ridotto in rovina, cadente"},
    {"word": "EMULO", "clue": "Rivale che cerca di eguagliare"},
    {"word": "FERINO", "clue": "Selvaggio, proprio delle belve"},
    {"word": "GRAMO", "clue": "Misero e stentato"},
    {"word": "IMBELLE", "clue": "Incapace di combattere, pavido"},
    {"word": "LACONICO", "clue": "Che parla con estrema brevita'"},
    {"word": "MANIERO", "clue": "Antica dimora fortificata"},
    {"word": "NUGOLO", "clue": "Sciame fitto e numeroso"},
    {"word": "OPIMO", "clue": "Ricco e abbondante"},
    {"word": "PALESE", "clue": "Chiaro e manifesto a tutti"},
    {"word": "QUERULO", "clue": "Che si lagna di continuo"},
    {"word": "RIBALDO", "clue": "Furfante privo di scrupoli"},
    {"word": "SCEVRO", "clue": "Privo, del tutto immune"},
    {"word": "TORVO", "clue": "Sguardo minaccioso e cupo"},
    {"word": "USBERGO", "clue": "Antica corazza del guerriero"},
    {"word": "VELIVOLO", "clue": "Aeromobile con le ali"},
    {"word": "ARGUTO", "clue": "Spiritoso e brillante nell'ingegno"},
    {"word": "BUCOLICO", "clue": "Della vita agreste e pastorale"},
    {"word": "CERULEO", "clue": "Dell'azzurro tenue del cielo"},
    {"word": "DISADORNO", "clue": "Spoglio di ogni ornamento"},
    {"word": "EBBRO", "clue": "Inebriato, fuori di se' dalla gioia"},
    {"word": "FALLACE", "clue": "Ingannevole, che induce in errore"},
    {"word": "GELIDO", "clue": "Freddo come il ghiaccio"},
    {"word": "IGNAVO", "clue": "Vile e privo di ogni ardore"},
    {"word": "LEGGIADRO", "clue": "Di grazia elegante e delicata"},
    {"word": "MENDACE", "clue": "Bugiardo, che dice il falso"},
    {"word": "NITIDO", "clue": "Limpido e perfettamente chiaro"},
    {"word": "OTTUSO", "clue": "Tardo di mente, poco acuto"},
    {"word": "PROCACE", "clue": "Sfrontato, provocante"},
    {"word": "RAUCO", "clue": "Dalla voce roca e velata"},
    {"word": "SUBLIME", "clue": "Che raggiunge la piu' alta grandezza"},
    {"word": "TENACE", "clue": "Che non molla la presa"},
    {"word": "UMBRATILE", "clue": "Schivo, amante dell'ombra e del ritiro"},
    {"word": "VERACE", "clue": "Autentico e sincero"},
    {"word": "ANELITO", "clue": "Ardente desiderio, aspirazione"},
    {"word": "BALDANZA", "clue": "Sicurezza spavalda di se'"},
    {"word": "CLEMENTE", "clue": "Indulgente, incline al perdono"},
    {"word": "DOVIZIA", "clue": "Grande abbondanza di beni"},
    {"word": "ESIMIO", "clue": "Illustre, di eccellente valore"},
    {"word": "FUGACE", "clue": "Che svanisce in un istante"},
    {"word": "GAGLIARDO", "clue": "Vigoroso e pieno di forza"},
    {"word": "INCLITO", "clue": "Celebre, glorioso"},
    {"word": "LIMPIDO", "clue": "Trasparente e puro"},
    {"word": "MERIGGIO", "clue": "Il pieno mezzogiorno assolato"},
    {"word": "NEGLETTO", "clue": "Trascurato, lasciato in abbandono"},
    {"word": "OSSEQUIO", "clue": "Rispettoso omaggio"},
    {"word": "PLACIDO", "clue": "Tranquillo e sereno"},
    {"word": "RECALCITRA", "clue": "Si oppone e resiste ostinato"},
    {"word": "SOLERTE", "clue": "Diligente e premuroso"},
    {"word": "TITUBANTE", "clue": "Esitante, incerto"},
    {"word": "UBERTOSO", "clue": "Fertile e rigoglioso"},
    {"word": "VINDICE", "clue": "Che punisce vendicando un torto"},
    {"word": "ADUSTO", "clue": "Arso e riarso dal sole"},
    {"word": "BIFIDO", "clue": "Diviso in due punte, come una lingua"},
    {"word": "CRUENTO", "clue": "Sanguinoso, feroce"},
    {"word": "DEROGA", "clue": "Eccezione a una norma"},
    {"word": "ESULE", "clue": "Chi vive lontano dalla patria per forza"},
    {"word": "FATIDICO", "clue": "Che annuncia il destino"},
    {"word": "GHERMIRE", "clue": "Afferrare con presa rapace"},
    {"word": "INDOMITO", "clue": "Che non si lascia domare"},
    {"word": "LUSINGA", "clue": "Adulazione che seduce"},
    {"word": "MONITO", "clue": "Severo avvertimento"},
    {"word": "OBSOLETO", "clue": "Caduto in disuso, antiquato"},
    {"word": "PERSPICACE", "clue": "Acuto nel comprendere a fondo"},
    {"word": "RAGGUARDE", "clue": "Notevole, degno di considerazione"},
    {"word": "SPRONE", "clue": "Stimolo che incita all'azione"},
    {"word": "TREGENDA", "clue": "Sabba di streghe, gran baccano"},
    {"word": "VETTA", "clue": "La cima piu' alta"},
]


def normalize_word(w: str) -> str:
    w = (w or "").strip().upper()
    w = "".join(c for c in unicodedata.normalize("NFD", w) if unicodedata.category(c) != "Mn")
    w = "".join(c for c in w if "A" <= c <= "Z")
    return w


def _attempt(items, max_words):
    grid = {}
    placements = []
    bbox = {"minr": 0, "maxr": 0, "minc": 0, "maxc": 0}

    def can_place(word, r, c, d):
        intersects = False
        for i, ch in enumerate(word):
            rr = r + (i if d == "down" else 0)
            cc = c + (i if d == "across" else 0)
            if (rr, cc) in grid:
                if grid[(rr, cc)] != ch:
                    return None
                intersects = True
            else:
                if d == "across":
                    if (rr - 1, cc) in grid or (rr + 1, cc) in grid:
                        return None
                else:
                    if (rr, cc - 1) in grid or (rr, cc + 1) in grid:
                        return None
        if d == "across":
            if (r, c - 1) in grid or (r, c + len(word)) in grid:
                return None
        else:
            if (r - 1, c) in grid or (r + len(word), c) in grid:
                return None
        return intersects

    def place(word, clue, r, c, d):
        for i, ch in enumerate(word):
            rr = r + (i if d == "down" else 0)
            cc = c + (i if d == "across" else 0)
            grid[(rr, cc)] = ch
            bbox["minr"] = min(bbox["minr"], rr)
            bbox["maxr"] = max(bbox["maxr"], rr)
            bbox["minc"] = min(bbox["minc"], cc)
            bbox["maxc"] = max(bbox["maxc"], cc)
        placements.append({"word": word, "clue": clue, "r": r, "c": c, "dir": d})

    first = items[0]
    place(first["word"], first["clue"], 0, 0, "across")

    for it in items[1:]:
        if len(placements) >= max_words:
            break
        word = it["word"]
        best = None
        cells = list(grid.items())
        random.shuffle(cells)
        for (cr, cc), letter in cells:
            for i, ch in enumerate(word):
                if ch != letter:
                    continue
                for d in ("down", "across"):
                    if d == "across":
                        r0, c0 = cr, cc - i
                    else:
                        r0, c0 = cr - i, cc
                    res = can_place(word, r0, c0, d)
                    if res:
                        inter = sum(
                            1
                            for k in range(len(word))
                            if (r0 + (k if d == "down" else 0), c0 + (k if d == "across" else 0)) in grid
                        )
                        endr = r0 + (len(word) - 1 if d == "down" else 0)
                        endc = c0 + (len(word) - 1 if d == "across" else 0)
                        nminr = min(bbox["minr"], r0)
                        nmaxr = max(bbox["maxr"], endr)
                        nminc = min(bbox["minc"], c0)
                        nmaxc = max(bbox["maxc"], endc)
                        span = max(nmaxr - nminr, nmaxc - nminc)
                        # prefer many intersections, then compactness
                        score = inter * 1000 - span * 10
                        if best is None or score > best[0]:
                            best = (score, word, it["clue"], r0, c0, d)
        if best:
            place(best[1], best[2], best[3], best[4], best[5])

    return grid, placements


def build_crossword(entries: list, max_words: int = 70, attempts: int = 12) -> dict | None:
    """entries: list of {word, clue}. Returns puzzle dict or None."""
    seen = set()
    items = []
    for e in entries:
        w = normalize_word(e.get("word", ""))
        clue = (e.get("clue") or "").strip()
        if 3 <= len(w) <= 11 and w not in seen and clue:
            seen.add(w)
            items.append({"word": w, "clue": clue})
    if len(items) < 6:
        return None
    items.sort(key=lambda x: len(x["word"]), reverse=True)

    best = None
    for _ in range(attempts):
        pool = items[:1] + random.sample(items[1:], len(items) - 1)
        grid, placements = _attempt(pool, max_words)
        if len(placements) < 6:
            continue
        rows = [r for (r, c) in grid]
        cols = [c for (r, c) in grid]
        span = max(max(rows) - min(rows), max(cols) - min(cols)) + 1
        # maximize words, then minimize span
        rank = (len(placements), -span)
        if best is None or rank > best[0]:
            best = (rank, grid, placements)

    if best is None:
        return None
    grid = best[1]
    placements = best[2]

    if len(placements) < 5:
        return None

    rows = [r for (r, c) in grid]
    cols = [c for (r, c) in grid]
    minr, minc = min(rows), min(cols)
    ngrid = {(r - minr, c - minc): l for (r, c), l in grid.items()}
    for p in placements:
        p["r"] -= minr
        p["c"] -= minc
    H = max(r for (r, c) in ngrid) + 1
    W = max(c for (r, c) in ngrid) + 1
    size = max(H, W)

    start_positions = sorted({(p["r"], p["c"]) for p in placements})
    number_at = {pos: i + 1 for i, pos in enumerate(start_positions)}

    across, down = [], []
    for p in placements:
        n = number_at.get((p["r"], p["c"]))
        entry = {
            "num": n,
            "clue": p["clue"],
            "answer": p["word"],
            "row": p["r"],
            "col": p["c"],
            "length": len(p["word"]),
            "direction": p["dir"],
        }
        (across if p["dir"] == "across" else down).append(entry)
    across.sort(key=lambda x: x["num"])
    down.sort(key=lambda x: x["num"])

    cells = []
    solution = {}
    for (r, c), l in sorted(ngrid.items()):
        cell = {"row": r, "col": c}
        if (r, c) in number_at:
            cell["number"] = number_at[(r, c)]
        cells.append(cell)
        solution[f"{r}-{c}"] = l

    return {"size": size, "cells": cells, "across": across, "down": down, "solution": solution}


def build_from_fallback(n: int = 90) -> dict | None:
    pool = FALLBACK_POOL[:]
    random.shuffle(pool)
    n = min(n, len(pool))
    for _ in range(4):
        puz = build_crossword(pool[:n], max_words=70, attempts=10)
        if puz:
            return puz
        random.shuffle(pool)
    return build_crossword(FALLBACK_POOL, max_words=70, attempts=6)


# ---------- Pool reale (14000+ definizioni), filtrato per difficolta' ----------
_TIER_ORDER = ["facilissima", "facile", "media", "alta", "altissima"]
_CLUES_POOL = None      # {word: clue}
_DIFFICULTY_POOL = None  # {word: tier}


def _load_pool_data():
    global _CLUES_POOL, _DIFFICULTY_POOL
    if _CLUES_POOL is None:
        root = os.path.dirname(__file__)
        with open(os.path.join(root, "data", "clues_by_word.json"), encoding="utf-8") as f:
            _CLUES_POOL = json.load(f)
        with open(os.path.join(root, "data", "word_difficulty.json"), encoding="utf-8") as f:
            _DIFFICULTY_POOL = json.load(f)


def load_pool(difficulty: str = "alta", limit: int = 260) -> list:
    """Entries {word, clue} per la difficolta' scelta (cumulativa: include anche i
    livelli piu' facili, cosi' il pool e' sempre abbastanza ricco per riempire uno schema)."""
    _load_pool_data()
    tier_idx = _TIER_ORDER.index(difficulty) if difficulty in _TIER_ORDER else len(_TIER_ORDER) - 1
    allowed_tiers = set(_TIER_ORDER[: tier_idx + 1])
    candidates = [
        {"word": w, "clue": c}
        for w, c in _CLUES_POOL.items()
        if 3 <= len(w) <= 11 and _DIFFICULTY_POOL.get(w, "altissima") in allowed_tiers
    ]
    random.shuffle(candidates)
    return candidates[:limit]


def build_from_pool(difficulty: str = "alta") -> dict | None:
    entries = load_pool(difficulty)
    if len(entries) < 15:
        return build_from_fallback()
    for _ in range(3):
        puz = build_crossword(entries, max_words=90, attempts=15)
        if puz:
            return puz
        entries = load_pool(difficulty)
    return build_from_fallback()