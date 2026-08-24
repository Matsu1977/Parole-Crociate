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
async def generate_words(n=70):
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage

        key = os.environ["EMERGENT_LLM_KEY"]
        chat = LlmChat(
            api_key=key,
            session_id=str(uuid.uuid4()),
            system_message=(
                "Sei un enigmista italiano di altissimo livello. Crei parole e definizioni "
                "raffinate, di difficolta' elevata, per cruciverba impegnativi stile Settimana Enigmistica."
            ),
        ).with_model("anthropic", "claude-sonnet-4-6")

        prompt = (
            f"Genera esattamente {n} voci per un grande cruciverba italiano di ALTA DIFFICOLTA'.\n"
            "Requisiti:\n"
            "- Parole italiane singole, da 3 a 11 lettere, senza spazi, senza trattini, senza nomi propri.\n"
            "- Mescola lunghezze diverse: includi molte parole corte (3-5 lettere) utili agli incroci "
            "e diverse parole lunghe.\n"
            "- Vocaboli ricercati, letterari, aulici o tecnici (non parole banali).\n"
            "- Definizioni brevi, eleganti e stimolanti, in italiano, senza mai citare la parola.\n"
            "- Nessuna parola ripetuta. Varia i campi semantici.\n"
            'Rispondi ESCLUSIVAMENTE con un array JSON valido nel formato: '
            '[{"word":"PAROLA","clue":"definizione"}]. Nessun testo prima o dopo.'
        )
        resp = await chat.send_message(UserMessage(text=prompt))
        text = resp if isinstance(resp, str) else str(resp)
        text = text.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1:
            text = text[start : end + 1]
        data = json.loads(text)
        out = [{"word": d["word"], "clue": d["clue"]} for d in data if d.get("word") and d.get("clue")]
        if len(out) >= 20:
            return out
    except Exception as e:
        logger.error(f"LLM word generation failed: {e}")
    return None


async def make_puzzle():
    words = await generate_words(70)
    if words:
        # blend fallback words to guarantee density and connectivity
        pool = words + random.sample(FALLBACK_POOL, min(40, len(FALLBACK_POOL)))
        random.shuffle(pool)
        puz = build_crossword(pool, max_words=70, attempts=12)
        if puz and (len(puz["across"]) + len(puz["down"])) >= 30:
            return puz
    logger.info("Using fallback puzzle pool")
    return build_from_fallback()


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
    return {
        "size": puzzle["size"],
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
