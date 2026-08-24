from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import json
import logging
import random
import string
import uuid
import asyncio
from pathlib import Path
from pydantic import BaseModel
from datetime import datetime, timezone

from crossword import build_crossword, build_from_fallback, FALLBACK_POOL
from italian_crossword import build_italian_crossword

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI()
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PLAYER_COLORS = ["#354A5F", "#C05C48"]


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def gen_code():
    return "".join(random.choice(string.ascii_uppercase) for _ in range(4))


# ---------- Puzzle generation ----------
async def generate_clues(words):
    """Return {WORD: clue} for the given Italian words via AI."""
    result = {}
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        from crossword import normalize_word

        key = os.environ["EMERGENT_LLM_KEY"]
        chat = LlmChat(
            api_key=key,
            session_id=str(uuid.uuid4()),
            system_message=(
                "Sei un enigmista italiano di altissimo livello: scrivi definizioni da cruciverba "
                "raffinate e impegnative, stile Settimana Enigmistica."
            ),
        ).with_model("anthropic", "claude-sonnet-4-6")

        uniq = sorted(set(words))
        prompt = (
            "Per OGNI parola italiana elencata scrivi UNA definizione da cruciverba di alta difficolta': "
            "breve, elegante, in italiano, senza mai usare o citare la parola stessa ne' i suoi derivati.\n"
            "Alcune possono essere forme flesse (plurali, voci verbali): definiscile comunque correttamente.\n"
            "Parole: " + ", ".join(uniq) + "\n"
            'Rispondi ESCLUSIVAMENTE con un oggetto JSON valido: {"PAROLA": "definizione", ...} '
            "contenente TUTTE le parole. Nessun testo prima o dopo."
        )
        resp = await chat.send_message(UserMessage(text=prompt))
        text = resp if isinstance(resp, str) else str(resp)
        text = text.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        s = text.find("{")
        e = text.rfind("}")
        if s != -1 and e != -1:
            text = text[s : e + 1]
        data = json.loads(text)
        for k, v in data.items():
            nk = normalize_word(k)
            if nk and v:
                result[nk] = str(v).strip()
    except Exception as ex:
        logger.error(f"clue generation failed: {ex}")
    return result


async def make_puzzle():
    loop = asyncio.get_event_loop()
    puz = None
    for _ in range(2):
        puz = await loop.run_in_executor(None, build_italian_crossword)
        if puz:
            break
    if not puz:
        logger.error("classic crossword build failed; using sparse fallback")
        return build_from_fallback()

    words = [e["answer"] for e in puz["across"]] + [e["answer"] for e in puz["down"]]
    clues = await generate_clues(words)
    for e in puz["across"] + puz["down"]:
        e["clue"] = clues.get(e["answer"]) or f"Vocabolo di {e['length']} lettere"
    return puz


async def generate_and_store(code):
    try:
        puzzle = await make_puzzle()
    except Exception as e:
        logger.error(f"generation failed for {code}: {e}")
        puzzle = build_from_fallback()
    await db.rooms.update_one(
        {"code": code}, {"$set": {"puzzle": puzzle, "status": "playing"}}
    )


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
        "entries": room.get("entries", {}),
        "players": players,
    }


# ---------- Models ----------
class JoinBody(BaseModel):
    name: str


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
async def create_room(body: JoinBody):
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "Nome richiesto")
    code = gen_code()
    while await db.rooms.find_one({"code": code}):
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
        "created_at": now_iso(),
    }
    await db.rooms.insert_one(room)
    asyncio.create_task(generate_and_store(code))
    return {"player": player, "state": room_state(room)}


@api_router.post("/rooms/{code}/join")
async def join_room(code: str, body: JoinBody):
    code = code.upper().strip()
    name = body.name.strip()
    room = await db.rooms.find_one({"code": code})
    if not room:
        raise HTTPException(404, "Stanza non trovata")
    players = room.get("players", [])
    existing = next((p for p in players if p["name"].lower() == name.lower()), None)
    if existing:
        existing["last_seen"] = now_iso()
        await db.rooms.update_one({"code": code}, {"$set": {"players": players}})
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
    await db.rooms.update_one({"code": code}, {"$set": {"players": players}})
    room["players"] = players
    return {"player": player, "state": room_state(room)}


@api_router.get("/rooms/{code}/puzzle")
async def get_puzzle(code: str):
    code = code.upper().strip()
    room = await db.rooms.find_one({"code": code})
    if not room:
        raise HTTPException(404, "Stanza non trovata")
    if not room.get("puzzle"):
        raise HTTPException(425, "Cruciverba in preparazione")
    return {"puzzle": public_puzzle(room["puzzle"])}


@api_router.get("/rooms/{code}/state")
async def get_state(code: str, player_id: str = ""):
    code = code.upper().strip()
    room = await db.rooms.find_one({"code": code})
    if not room:
        raise HTTPException(404, "Stanza non trovata")
    if player_id:
        players = room.get("players", [])
        for p in players:
            if p["id"] == player_id:
                p["last_seen"] = now_iso()
        await db.rooms.update_one({"code": code}, {"$set": {"players": players}})
        room["players"] = players
    return room_state(room, player_id)


@api_router.post("/rooms/{code}/cell")
async def set_cell(code: str, body: CellBody):
    code = code.upper().strip()
    room = await db.rooms.find_one({"code": code})
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

    status = room.get("status", "playing")
    if all(entries.get(k, {}).get("letter") == v for k, v in solution.items()):
        status = "completed"

    update = {"entries": entries, "status": status}
    if status == "completed" and room.get("status") != "completed":
        update["completed_at"] = now_iso()
    await db.rooms.update_one({"code": code}, {"$set": update})
    room["entries"] = entries
    room["status"] = status
    return room_state(room)


@api_router.post("/rooms/{code}/focus")
async def set_focus(code: str, body: FocusBody):
    code = code.upper().strip()
    room = await db.rooms.find_one({"code": code})
    if not room:
        raise HTTPException(404, "Stanza non trovata")
    players = room.get("players", [])
    for p in players:
        if p["id"] == body.player_id:
            p["focus"] = {"row": body.row, "col": body.col, "direction": body.direction}
            p["last_seen"] = now_iso()
    await db.rooms.update_one({"code": code}, {"$set": {"players": players}})
    return {"ok": True}


@api_router.post("/rooms/{code}/new")
async def new_puzzle(code: str):
    code = code.upper().strip()
    room = await db.rooms.find_one({"code": code})
    if not room:
        raise HTTPException(404, "Stanza non trovata")
    await db.rooms.update_one(
        {"code": code},
        {"$set": {"puzzle": None, "entries": {}, "status": "generating", "created_at": now_iso()}},
    )
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


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
