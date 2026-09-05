from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import json
import logging
import secrets
import string
import uuid
import asyncio
from pathlib import Path
from pydantic import BaseModel
from datetime import datetime, timezone

from crossword import build_from_fallback
from italian_crossword import build_italian_crossword

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# Le stanze vivono solo in RAM: niente database esterno.
# Si azzerano a ogni riavvio del server, va benissimo per un gioco cosi'.
ROOMS: dict = {}

app = FastAPI()
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PLAYER_COLORS = ["#354A5F", "#C05C48"]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def gen_code() -> str:
    return "".join(secrets.choice(string.ascii_uppercase) for _ in range(4))


# ---------- Puzzle generation ----------
DIFFICULTY_PROMPTS = {
    "facilissima": "di difficolta' FACILISSIMA: solo parole molto comuni, griglia piccola",
    "facile": "di difficolta' FACILE: parole comuni, griglia ridotta",
    "media": (
        "di difficolta' MEDIA: definizioni chiare, dirette e comprensibili, "
        "con qualche piccola sfida ma senza tranelli"
    ),
    "alta": (
        "di difficolta' ALTA: definizioni ricercate, eleganti e stimolanti, "
        "con vocabolario elevato"
    ),
    "altissima": (
        "di difficolta' ALTISSIMA: definizioni criptiche e allusive, con doppi sensi, "
        "metafore e giochi di parole, molto impegnative da decifrare"
    ),
}


_CLUES = None


def load_clues():
    """Load the local Italian WordNet definitions once per server process."""
    global _CLUES
    if _CLUES is None:
        clue_path = ROOT_DIR / "data" / "clues_by_word.json"
        with open(clue_path, encoding="utf-8") as file:
            _CLUES = json.load(file)
        logger.info("Loaded %s local crossword definitions", len(_CLUES))
    return _CLUES


async def make_puzzle(difficulty="alta"):
    loop = asyncio.get_event_loop()

    puz = await loop.run_in_executor(None, lambda: build_italian_crossword(difficulty=difficulty))
    if not puz:
        logger.error("classic crossword build failed; using sparse fallback")
        return build_from_fallback()

    clues = load_clues()
    for e in puz["across"] + puz["down"]:
        e["clue"] = clues.get(e["answer"]) or "Definizione non disponibile"
    return puz


async def generate_and_store(code):
    room = ROOMS.get(code)
    difficulty = (room or {}).get("difficulty", "alta")
    try:
        puzzle = await make_puzzle(difficulty)
    except Exception as e:
        logger.error(f"generation failed for {code}: {e}")
        puzzle = build_from_fallback()
    if room is not None:
        room["puzzle"] = puzzle
        room["status"] = "playing"


def public_puzzle(puzzle):
    rows = puzzle.get("rows", puzzle.get("size"))
    cols = puzzle.get("cols", puzzle.get("size"))
    return {
        "rows": rows,
        "cols": cols,
        "cells": puzzle["cells"],
        "across": [{k: v for k, v in c.items() if k != "answer"} for c in puzzle["across"]],
        "down": [{k: v for k, v in c.items() if k != "answer"} for c in puzzle["down"]],
    }


def room_state(room, player_id=None):
    players = []
    for p in room.get("players", []):
        players.append(
            {
                "id": p["id"],
                "name": p["name"],
                "index": p["index"],
                "color": p["color"],
                "focus": p.get("focus"),
                "last_seen": p.get("last_seen"),
            }
        )
    return {
        "code": room["code"],
        "status": room.get("status", "playing"),
        "puzzle_ready": room.get("puzzle") is not None,
        "difficulty": room.get("difficulty", "alta"),
        "entries": room.get("entries", {}),
        "players": players,
    }


# ---------- Models ----------
class JoinBody(BaseModel):
    name: str


class CreateBody(BaseModel):
    name: str
    difficulty: str = "alta"


class CellBody(BaseModel):
    player_id: str
    row: int
    col: int
    letter: str


class FocusBody(BaseModel):
    player_id: str
    row: int
    col: int
    direction: str


# ---------- Routes ----------
@api_router.get("/")
async def root():
    return {"message": "Cruciverba Insieme API"}


@api_router.post("/rooms")
async def create_room(body: CreateBody):
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "Nome richiesto")
    difficulty = body.difficulty if body.difficulty in DIFFICULTY_PROMPTS else "alta"
    code = gen_code()
    while code in ROOMS:
        code = gen_code()
    player = {
        "id": str(uuid.uuid4()),
        "name": name,
        "index": 0,
        "color": PLAYER_COLORS[0],
        "last_seen": now_iso(),
        "focus": None,
    }
    room = {
        "code": code,
        "puzzle": None,
        "entries": {},
        "players": [player],
        "status": "generating",
        "difficulty": difficulty,
        "created_at": now_iso(),
    }
    ROOMS[code] = room
    asyncio.create_task(generate_and_store(code))
    return {"player": player, "state": room_state(room)}


@api_router.post("/rooms/{code}/join")
async def join_room(code: str, body: JoinBody):
    code = code.upper().strip()
    name = body.name.strip()
    room = ROOMS.get(code)
    if not room:
        raise HTTPException(404, "Stanza non trovata")
    players = room.get("players", [])
    existing = next((p for p in players if p["name"].lower() == name.lower()), None)
    if existing:
        existing["last_seen"] = now_iso()
        return {"player": existing, "state": room_state(room)}
    if len(players) >= 2:
        raise HTTPException(403, "La stanza e' gia' al completo")
    idx = len(players)
    player = {
        "id": str(uuid.uuid4()),
        "name": name,
        "index": idx,
        "color": PLAYER_COLORS[idx],
        "last_seen": now_iso(),
        "focus": None,
    }
    players.append(player)
    room["players"] = players
    return {"player": player, "state": room_state(room)}


@api_router.get("/rooms/{code}/puzzle")
async def get_puzzle(code: str):
    code = code.upper().strip()
    room = ROOMS.get(code)
    if not room:
        raise HTTPException(404, "Stanza non trovata")
    if not room.get("puzzle"):
        raise HTTPException(425, "Cruciverba in preparazione")
    return {"puzzle": public_puzzle(room["puzzle"])}


@api_router.get("/rooms/{code}/state")
async def get_state(code: str, player_id: str = ""):
    code = code.upper().strip()
    room = ROOMS.get(code)
    if not room:
        raise HTTPException(404, "Stanza non trovata")
    if player_id:
        players = room.get("players", [])
        for p in players:
            if p["id"] == player_id:
                p["last_seen"] = now_iso()
        room["players"] = players
    return room_state(room, player_id)


@api_router.post("/rooms/{code}/cell")
async def set_cell(code: str, body: CellBody):
    code = code.upper().strip()
    room = ROOMS.get(code)
    if not room:
        raise HTTPException(404, "Stanza non trovata")
    if not room.get("puzzle"):
        raise HTTPException(425, "Cruciverba in preparazione")
    key = f"{body.row}-{body.col}"
    solution = room["puzzle"]["solution"]
    if key not in solution:
        raise HTTPException(400, "Cella non valida")
    entries = room.get("entries", {})
    letter = body.letter.strip().upper()[:1]
    if letter:
        entries[key] = {"letter": letter, "playerId": body.player_id}
    else:
        entries.pop(key, None)

    old_status = room.get("status", "playing")
    status = old_status
    if all(entries.get(k, {}).get("letter") == v for k, v in solution.items()):
        status = "completed"

    room["entries"] = entries
    room["status"] = status
    if status == "completed" and old_status != "completed":
        room["completed_at"] = now_iso()
    return room_state(room)


@api_router.post("/rooms/{code}/focus")
async def set_focus(code: str, body: FocusBody):
    code = code.upper().strip()
    room = ROOMS.get(code)
    if not room:
        raise HTTPException(404, "Stanza non trovata")
    players = room.get("players", [])
    for p in players:
        if p["id"] == body.player_id:
            p["focus"] = {"row": body.row, "col": body.col, "direction": body.direction}
            p["last_seen"] = now_iso()
    return {"ok": True}


@api_router.post("/rooms/{code}/new")
async def new_puzzle(code: str):
    code = code.upper().strip()
    room = ROOMS.get(code)
    if not room:
        raise HTTPException(404, "Stanza non trovata")
    room["puzzle"] = None
    room["entries"] = {}
    room["status"] = "generating"
    room["created_at"] = now_iso()
    asyncio.create_task(generate_and_store(code))
    return {"status": "generating"}


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)