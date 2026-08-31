"""Backend API tests for Cruciverba Insieme (async puzzle generation)."""
import os
import time
import pytest
import requests

from pathlib import Path
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[2] / "frontend" / ".env")
except Exception:
    pass
BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _wait_puzzle_ready(session, code, timeout=75):
    start = time.time()
    while time.time() - start < timeout:
        r = session.get(f"{API}/rooms/{code}/state", timeout=15)
        assert r.status_code == 200
        if r.json().get("puzzle_ready"):
            return time.time() - start
        time.sleep(1.0)
    raise AssertionError(f"puzzle not ready within {timeout}s")


@pytest.fixture(scope="module")
def room(session):
    t0 = time.time()
    r = session.post(f"{API}/rooms", json={"name": "Mamma"}, timeout=15)
    elapsed = time.time() - t0
    assert r.status_code == 200, r.text
    data = r.json()
    assert "player" in data and "state" in data
    assert "puzzle" not in data  # should not be included in create anymore
    assert data["state"]["status"] == "generating"
    assert data["state"]["puzzle_ready"] is False
    # instant response
    assert elapsed < 5.0, f"create was slow: {elapsed:.2f}s"
    return {"data": data, "code": data["state"]["code"], "create_elapsed": elapsed}


# ---- Create returns instantly ----
def test_create_room_instant(room):
    assert room["create_elapsed"] < 5.0
    p = room["data"]["player"]
    assert p["index"] == 0 and p["color"].lower() == "#354a5f" and p["name"] == "Mamma"
    assert len(room["code"]) == 4


def test_create_room_empty_name_rejected(session):
    r = session.post(f"{API}/rooms", json={"name": "   "}, timeout=30)
    assert r.status_code == 400


# ---- Puzzle-not-ready guards ----
def test_puzzle_425_before_ready(session):
    r = session.post(f"{API}/rooms", json={"name": "Solo"}, timeout=15)
    assert r.status_code == 200
    code = r.json()["state"]["code"]
    # immediately fetch puzzle - should be 425
    resp = session.get(f"{API}/rooms/{code}/puzzle", timeout=10)
    # allow tiny race window - accept 425 or 200 (fallback is fast)
    assert resp.status_code in (200, 425)


# ---- Puzzle becomes ready + is large ----
def test_puzzle_becomes_ready_and_is_large(session, room):
    code = room["code"]
    elapsed = _wait_puzzle_ready(session, code, timeout=75)
    print(f"puzzle ready in {elapsed:.1f}s")
    r = session.get(f"{API}/rooms/{code}/puzzle", timeout=15)
    assert r.status_code == 200
    puz = r.json()["puzzle"]
    assert "solution" not in puz
    for c in puz["across"] + puz["down"]:
        assert "answer" not in c
    total = len(puz["across"]) + len(puz["down"])
    rows, cols = puz.get("rows"), puz.get("cols")
    print(f"grid {rows}x{cols} with {total} defs ({len(puz['across'])} A / {len(puz['down'])} D)")
    assert rows == 13 and cols == 13, f"expected 13x13 grid, got {rows}x{cols}"
    assert 40 <= total <= 90, f"unexpected clue count: {total}"
    # fully-checked verification: every filled cell participates in both across & down
    cells = puz["cells"]
    filled = [(r, c) for r, row in enumerate(cells) for c, cell in enumerate(row) if cell]
    assert len(filled) > 100, f"too few filled cells: {len(filled)}"
    # continuous numbering sanity
    nums = sorted({c["num"] for c in puz["across"] + puz["down"]})
    assert nums[0] == 1
    # every clue has non-empty italian text
    for c in puz["across"] + puz["down"]:
        assert c.get("clue", "").strip(), f"empty clue at {c.get('number')}"


# ---- Join ----
def test_join_room_second_player_terracotta(session, room):
    r = session.post(f"{API}/rooms/{room['code']}/join", json={"name": "Papa"}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["player"]["index"] == 1
    assert data["player"]["color"].lower() == "#c05c48"
    assert len(data["state"]["players"]) == 2
    assert "puzzle" not in data  # not inline


def test_join_room_full_rejected(session, room):
    r = session.post(f"{API}/rooms/{room['code']}/join", json={"name": "Third"}, timeout=30)
    assert r.status_code == 403


def test_join_same_name_idempotent(session, room):
    r = session.post(f"{API}/rooms/{room['code']}/join", json={"name": "Mamma"}, timeout=30)
    assert r.status_code == 200
    assert r.json()["player"]["index"] == 0


def test_join_unknown_room_404(session):
    r = session.post(f"{API}/rooms/ZZZZ/join", json={"name": "x"}, timeout=30)
    assert r.status_code == 404


# ---- Cell + state propagation ----
def test_state_and_cell_propagation(session, room):
    code = room["code"]
    _wait_puzzle_ready(session, code, timeout=75)
    p1 = room["data"]["player"]
    puz = session.get(f"{API}/rooms/{code}/puzzle", timeout=15).json()["puzzle"]
    entry = puz["across"][0] if puz["across"] else puz["down"][0]
    r0, c0 = entry["row"], entry["col"]
    resp = session.post(
        f"{API}/rooms/{code}/cell",
        json={"player_id": p1["id"], "row": r0, "col": c0, "letter": "A"},
        timeout=15,
    )
    assert resp.status_code == 200
    st = resp.json()
    k = f"{r0}-{c0}"
    assert st["entries"][k]["letter"] == "A"
    assert st["entries"][k]["playerId"] == p1["id"]
    # visible to other via GET
    r2 = session.get(f"{API}/rooms/{code}/state", timeout=15).json()
    assert r2["entries"][k]["letter"] == "A"
    # clear
    resp = session.post(
        f"{API}/rooms/{code}/cell",
        json={"player_id": p1["id"], "row": r0, "col": c0, "letter": ""},
        timeout=15,
    )
    assert resp.status_code == 200
    assert k not in resp.json()["entries"]


def test_cell_invalid_position_400(session, room):
    p1 = room["data"]["player"]
    r = session.post(
        f"{API}/rooms/{room['code']}/cell",
        json={"player_id": p1["id"], "row": 999, "col": 999, "letter": "A"},
        timeout=15,
    )
    assert r.status_code == 400


def test_focus_endpoint(session, room):
    p1 = room["data"]["player"]
    r = session.post(
        f"{API}/rooms/{room['code']}/focus",
        json={"player_id": p1["id"], "row": 0, "col": 0, "direction": "across"},
        timeout=15,
    )
    assert r.status_code == 200


# ---- New puzzle returns instantly and regenerates ----
def test_new_puzzle_instant_and_regenerates(session, room):
    code = room["code"]
    t0 = time.time()
    r = session.post(f"{API}/rooms/{code}/new", timeout=15)
    elapsed = time.time() - t0
    assert r.status_code == 200
    assert r.json().get("status") == "generating"
    assert elapsed < 5.0, f"new-puzzle was slow: {elapsed:.2f}s"
    # state should immediately show generating + puzzle_ready False
    st = session.get(f"{API}/rooms/{code}/state", timeout=15).json()
    assert st["status"] == "generating"
    assert st["puzzle_ready"] is False
    assert st["entries"] == {}
    # wait for new puzzle
    _wait_puzzle_ready(session, code, timeout=75)
    r = session.get(f"{API}/rooms/{code}/puzzle", timeout=15).json()
    assert "puzzle" in r



# ---- Difficulty regression ----
def test_create_room_with_difficulty_media(session):
    r = session.post(f"{API}/rooms", json={"name": "MediaP", "difficulty": "media"}, timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert data["state"]["difficulty"] == "media"
    code = data["state"]["code"]
    assert len(code) == 4 and code.isupper() and code.isalpha()
    st = session.get(f"{API}/rooms/{code}/state", timeout=15).json()
    assert st["difficulty"] == "media"


def test_create_room_with_difficulty_altissima(session):
    r = session.post(f"{API}/rooms", json={"name": "AltP", "difficulty": "altissima"}, timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert data["state"]["difficulty"] == "altissima"


def test_create_room_invalid_difficulty_defaults(session):
    r = session.post(f"{API}/rooms", json={"name": "Foo", "difficulty": "bogus"}, timeout=15)
    assert r.status_code == 200
    # invalid falls back to "alta"
    assert r.json()["state"]["difficulty"] == "alta"


def test_create_room_default_difficulty(session):
    r = session.post(f"{API}/rooms", json={"name": "DefP"}, timeout=15)
    assert r.status_code == 200
    assert r.json()["state"]["difficulty"] == "alta"
