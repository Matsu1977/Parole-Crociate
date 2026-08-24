# Cruciverba Insieme — PRD

## Problem statement (original)
"Vorrei costruire una web app per giocare in contemporanea con mia madre, io vivo in Giappone lei in Italia, a dei cruciverba. Il livello dei cruciverba deve essere alto." + follow-up: creazione stanza "resta a caricare / va in errore"; vuole un cruciverba GRANDE tipo Settimana Enigmistica con ~50-70 definizioni.

## User choices
- Gioco in tempo reale sulla stessa griglia
- Cruciverba generati dall'AI in italiano, alta difficoltà
- Nessun login: nome + codice-stanza condiviso
- Solo italiano, nessun extra
- Griglia grande: ~50-70 definizioni

## Personas
- Figlio (Giappone) e Madre (Italia): due giocatori che risolvono insieme un cruciverba impegnativo a distanza.

## Architecture
- Backend: FastAPI + MongoDB (motor). Routes /api. Rooms collection.
- AI: emergentintegrations LlmChat + EMERGENT_LLM_KEY, modello anthropic claude-sonnet-4-6, genera ~70 voci italiane difficili (word+clue) in JSON.
- Crossword builder (crossword.py): algoritmo greedy con più tentativi, scelta per numero incroci + compattezza. FALLBACK_POOL ~115 parole difficili se l'AI fallisce.
- Generazione ASINCRONA: POST /rooms crea la stanza all'istante (status 'generating'), genera in background (asyncio task), il client fa polling di /state finché puzzle_ready e poi scarica /puzzle.
- Real-time: polling ogni 1200ms su /state (entries, players, presence). POST /cell con attribuzione giocatore; win detection server-side. POST /focus per la presenza.
- Frontend: React + Tailwind. Landing (crea/unisci), Game (griglia + pannello indizi + presenza + attesa + vittoria). Colori giocatori: P1 #354A5F, P2 #C05C48.

## Implemented (2026-06)
- [x] Landing IT con crea/unisci stanza (design editorial warm)
- [x] Generazione in background (fix "resta a caricare") + schermata di attesa con codice/condivisione
- [x] Griglia collaborativa in tempo reale con colori per giocatore
- [x] Presenza giocatori, indizi Orizzontali/Verticali, banner indizio attivo
- [x] Navigazione tastiera (frecce, spazio cambia direzione, backspace)
- [x] Rilevamento completamento + overlay vittoria + nuovo cruciverba
- [x] MOTORE CLASSICO "a incastro totale" (Settimana Enigmistica): griglia rettangolare 13x13 piena, caselle nere, ogni casella incrociata orizz+vert, numerazione continua, ~55-62 definizioni
  - Dizionario italiano 592k parole (backend/data/words_by_len.json), generazione pattern costruttiva (run-splitting, min 3/max 8), riempimento a backtracking con bitset (~5-15s)
  - Definizioni di alta difficoltà generate dall'AI (Claude) per ogni parola trovata, in un'unica chiamata batch
- Verificato dal testing agent iteration_1/2/3: backend 100%, frontend 100%.

## Architettura motore cruciverba
- backend/italian_crossword.py: gen_pattern (costruttivo), get_slots, solve (bitset FC + restart), build_italian_crossword, _assemble -> {rows, cols, cells, across, down, solution}
- backend/crossword.py: fallback sparso (ultima risorsa)
- backend/prep_words.py: preprocessa il dizionario grezzo in words_by_len.json
- Puzzle pubblico: rows/cols/cells/across/down (senza answer/solution). Chiave numero indizio = 'num'.

## Note
- Generazione ~30-60s (riempimento griglia + scrittura definizioni AI): gestita in background con schermata di attesa.
- Dimensione max griglia limitata a 13x13 dal dizionario (parole fino a 13 lettere) e dalla riempibilita' affidabile.

## Backlog / next (P1/P2)
- P1: chat tra i due giocatori durante il gioco
- P1: timer e cronologia partite
- P2: livelli di difficoltà selezionabili / temi
- P2: TTL index sulle stanze (cleanup), controllo player_id su /new
- P2: WebSocket al posto del polling per scala
