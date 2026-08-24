import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import { Loader2, Share2, Sparkles, PartyPopper, Home } from "lucide-react";
import { joinRoom, getState, getPuzzle, setCell, setFocus, newPuzzle } from "@/lib/api";
import CrosswordGrid from "@/components/CrosswordGrid";
import CluePanel from "@/components/CluePanel";

const key = (r, c) => `${r}-${c}`;

export default function Game() {
  const { code } = useParams();
  const nav = useNavigate();

  const [player, setPlayer] = useState(null);
  const [puzzle, setPuzzle] = useState(null);
  const [entries, setEntries] = useState({});
  const [players, setPlayers] = useState([]);
  const [status, setStatus] = useState("playing");
  const [selected, setSelected] = useState(null);
  const [direction, setDirection] = useState("across");
  const [poppedKey, setPoppedKey] = useState(null);
  const [loading, setLoading] = useState(true);

  const inputRef = useRef(null);
  const pendingRef = useRef(new Map());
  const lastFocusRef = useRef(0);
  const puzzleReadyRef = useRef(false);
  const fetchingRef = useRef(false);

  const loadPuzzle = useCallback(async () => {
    if (fetchingRef.current || puzzleReadyRef.current) return;
    fetchingRef.current = true;
    try {
      const pz = await getPuzzle(code);
      puzzleReadyRef.current = true;
      setPuzzle(pz.puzzle);
      const first = pz.puzzle.across[0] || pz.puzzle.down[0];
      if (first) {
        setSelected({ row: first.row, col: first.col });
        setDirection(first.direction);
      }
    } catch (e) {
      /* not ready yet */
    } finally {
      fetchingRef.current = false;
    }
  }, [code]);

  // ---- derived puzzle structures ----
  const { cellSet, numberMap, acrossAt, downAt } = useMemo(() => {
    const cs = new Set();
    const nm = {};
    const aAt = {};
    const dAt = {};
    if (puzzle) {
      puzzle.cells.forEach((c) => {
        cs.add(key(c.row, c.col));
        if (c.number != null) nm[key(c.row, c.col)] = c.number;
      });
      const map = (clues, dir, store) =>
        clues.forEach((cl) => {
          for (let i = 0; i < cl.length; i++) {
            const r = cl.row + (dir === "down" ? i : 0);
            const c = cl.col + (dir === "across" ? i : 0);
            store[key(r, c)] = cl;
          }
        });
      map(puzzle.across, "across", aAt);
      map(puzzle.down, "down", dAt);
    }
    return { cellSet: cs, numberMap: nm, acrossAt: aAt, downAt: dAt };
  }, [puzzle]);

  const playersById = useMemo(() => {
    const m = {};
    players.forEach((p) => (m[p.id] = p));
    return m;
  }, [players]);

  const activeClue = useMemo(() => {
    if (!selected) return null;
    const store = direction === "across" ? acrossAt : downAt;
    return store[key(selected.row, selected.col)] || null;
  }, [selected, direction, acrossAt, downAt]);

  const activeKeys = useMemo(() => {
    const s = new Set();
    if (activeClue) {
      for (let i = 0; i < activeClue.length; i++) {
        const r = activeClue.row + (activeClue.direction === "down" ? i : 0);
        const c = activeClue.col + (activeClue.direction === "across" ? i : 0);
        s.add(key(r, c));
      }
    }
    return s;
  }, [activeClue]);

  const other = players.find((p) => player && p.id !== player.id);
  const otherFocusKey = other?.focus ? key(other.focus.row, other.focus.col) : null;

  // ---- initial join ----
  useEffect(() => {
    const name = sessionStorage.getItem(`cw_name_${code}`);
    if (!name) {
      nav("/");
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const data = await joinRoom(code, name);
        if (cancelled) return;
        setPlayer(data.player);
        setPlayers(data.state.players || []);
        setEntries(data.state.entries || {});
        setStatus(data.state.status);
        if (data.state.puzzle_ready) {
          await loadPuzzle();
        }
      } catch (e) {
        toast.error(e?.response?.data?.detail || "Impossibile entrare nella stanza");
        nav("/");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [code, nav]);

  // ---- polling ----
  useEffect(() => {
    if (!player) return;
    let stop = false;
    const poll = async () => {
      try {
        const st = await getState(code, player.id);
        if (stop) return;
        if (st.puzzle_ready && !puzzleReadyRef.current) {
          loadPuzzle();
        }
        const server = st.entries || {};
        const merged = { ...server };
        const nowT = Date.now();
        for (const [k, v] of pendingRef.current) {
          if (nowT - v.ts > 2500) {
            pendingRef.current.delete(k);
            continue;
          }
          if (v.letter) merged[k] = { letter: v.letter, playerId: player.id };
          else delete merged[k];
        }
        setEntries(merged);
        setPlayers(st.players || []);
        setStatus(st.status);
      } catch (e) {
        /* ignore transient */
      }
    };
    poll();
    const id = setInterval(poll, 1200);
    return () => {
      stop = true;
      clearInterval(id);
    };
  }, [player, code]);

  // ---- presence ----
  useEffect(() => {
    if (!player || !selected) return;
    const t = Date.now();
    if (t - lastFocusRef.current < 250) return;
    lastFocusRef.current = t;
    setFocus(code, player.id, selected.row, selected.col, direction).catch(() => {});
  }, [selected, direction, player, code]);

  const focusInput = () => {
    if (inputRef.current) inputRef.current.focus({ preventScroll: true });
  };

  const selectCell = (r, c, preferDir) => {
    if (!cellSet.has(key(r, c))) return;
    let dir = preferDir || direction;
    const hasAcross = !!acrossAt[key(r, c)];
    const hasDown = !!downAt[key(r, c)];
    if (dir === "across" && !hasAcross && hasDown) dir = "down";
    if (dir === "down" && !hasDown && hasAcross) dir = "across";
    setSelected({ row: r, col: c });
    setDirection(dir);
    focusInput();
  };

  const onCellClick = (r, c) => {
    if (selected && selected.row === r && selected.col === c) {
      // toggle direction if possible
      const otherDir = direction === "across" ? "down" : "across";
      const store = otherDir === "across" ? acrossAt : downAt;
      if (store[key(r, c)]) setDirection(otherDir);
      focusInput();
      return;
    }
    selectCell(r, c);
  };

  const commitLetter = useCallback(
    (r, c, letter) => {
      const k = key(r, c);
      const val = { letter, playerId: player.id };
      setEntries((prev) => ({ ...prev, [k]: val }));
      pendingRef.current.set(k, { letter, ts: Date.now() });
      setPoppedKey(k);
      setTimeout(() => setPoppedKey((p) => (p === k ? null : p)), 160);
      setCell(code, player.id, r, c, letter).catch(() => {});
    },
    [player, code]
  );

  const clearCell = useCallback(
    (r, c) => {
      const k = key(r, c);
      setEntries((prev) => {
        const n = { ...prev };
        delete n[k];
        return n;
      });
      pendingRef.current.set(k, { letter: "", ts: Date.now() });
      setCell(code, player.id, r, c, "").catch(() => {});
    },
    [player, code]
  );

  const moveInClue = (delta) => {
    if (!activeClue || !selected) return;
    const idx =
      activeClue.direction === "across"
        ? selected.col - activeClue.col
        : selected.row - activeClue.row;
    const ni = idx + delta;
    if (ni < 0 || ni >= activeClue.length) return;
    const r = activeClue.row + (activeClue.direction === "down" ? ni : 0);
    const c = activeClue.col + (activeClue.direction === "across" ? ni : 0);
    setSelected({ row: r, col: c });
  };

  const step = (dr, dc) => {
    if (!selected) return;
    let r = selected.row + dr;
    let c = selected.col + dc;
    while (r >= 0 && c >= 0 && r < puzzle.rows && c < puzzle.cols) {
      if (cellSet.has(key(r, c))) {
        selectCell(r, c, dr !== 0 ? "down" : "across");
        return;
      }
      r += dr;
      c += dc;
    }
  };

  const handleLetter = (raw) => {
    if (!selected || status === "completed") return;
    const ch = raw.toUpperCase().replace(/[^A-Z]/g, "").slice(-1);
    if (!ch) return;
    commitLetter(selected.row, selected.col, ch);
    moveInClue(1);
  };

  const onKeyDown = (e) => {
    if (!selected) return;
    const k = e.key;
    if (/^[a-zA-Z]$/.test(k)) {
      e.preventDefault();
      handleLetter(k);
      return;
    }
    if (k === "Backspace") {
      e.preventDefault();
      const curKey = key(selected.row, selected.col);
      if (entries[curKey]?.letter) {
        clearCell(selected.row, selected.col);
      } else {
        moveInClue(-1);
        const idx =
          activeClue &&
          (activeClue.direction === "across"
            ? selected.col - activeClue.col
            : selected.row - activeClue.row);
        if (activeClue && idx > 0) {
          const ni = idx - 1;
          const r = activeClue.row + (activeClue.direction === "down" ? ni : 0);
          const c = activeClue.col + (activeClue.direction === "across" ? ni : 0);
          clearCell(r, c);
        }
      }
      return;
    }
    if (k === " ") {
      e.preventDefault();
      const otherDir = direction === "across" ? "down" : "across";
      const store = otherDir === "across" ? acrossAt : downAt;
      if (store[key(selected.row, selected.col)]) setDirection(otherDir);
      return;
    }
    if (k === "ArrowRight") { e.preventDefault(); step(0, 1); }
    else if (k === "ArrowLeft") { e.preventDefault(); step(0, -1); }
    else if (k === "ArrowDown") { e.preventDefault(); step(1, 0); }
    else if (k === "ArrowUp") { e.preventDefault(); step(-1, 0); }
  };

  const selectClue = (clue, dir) => {
    setDirection(dir);
    setSelected({ row: clue.row, col: clue.col });
    focusInput();
  };

  const share = () => {
    const url = `${window.location.origin}/stanza/${code}`;
    navigator.clipboard?.writeText(url).then(
      () => toast.success("Link copiato! Invialo per giocare insieme."),
      () => toast.message(url)
    );
  };

  const startNew = async () => {
    try {
      setStatus("generating");
      setPuzzle(null);
      setSelected(null);
      setEntries({});
      pendingRef.current.clear();
      puzzleReadyRef.current = false;
      await newPuzzle(code);
      toast.message("Sto preparando un nuovo cruciverba…");
    } catch (e) {
      toast.error("Impossibile generare un nuovo cruciverba");
    }
  };

  const isOnline = (p) => {
    if (!p?.last_seen) return false;
    return Date.now() - new Date(p.last_seen).getTime() < 15000;
  };

  if (!player) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4">
        <Loader2 className="animate-spin text-[#c05c48]" size={28} />
        <p className="font-serif text-2xl text-[#2c2a29]">Entro nella stanza…</p>
      </div>
    );
  }

  if (!puzzle) {
    return (
      <div className="min-h-screen relative flex flex-col items-center justify-center px-6 text-center">
        <div className="paper-texture absolute inset-0 z-0" />
        <div className="relative z-10 fade-up max-w-lg">
          <Loader2 className="animate-spin text-[#c05c48] mx-auto" size={32} />
          <h1 className="font-serif text-4xl sm:text-5xl text-[#2c2a29] mt-6">
            Sto componendo il cruciverba
          </h1>
          <p className="text-[#5c5856] mt-3 leading-relaxed">
            Un grande schema con definizioni di alto livello. Ci vogliono pochi istanti.
          </p>

          <div className="mt-10 inline-flex flex-col items-center gap-4 rounded-lg bg-[#ffffff] border border-[#d6cec2] px-8 py-6">
            <span className="font-mono text-[0.7rem] tracking-[0.3em] uppercase text-[#8a8481]">
              Codice stanza
            </span>
            <span className="font-mono text-4xl tracking-[0.4em] text-[#2c2a29]">{code}</span>
            <button
              data-testid="share-button"
              onClick={share}
              className="flex items-center gap-2 rounded-full bg-[#2c2a29] hover:bg-[#5c5856] text-[#f9f6f0] px-6 py-2.5 text-sm transition-colors"
            >
              <Share2 size={15} />
              Copia il link e invitala
            </button>
          </div>

          <div className="mt-8 flex items-center justify-center gap-3" data-testid="presence">
            {players.map((p) => (
              <div key={p.id} className="flex items-center gap-1.5">
                <span
                  className="w-2.5 h-2.5 rounded-full"
                  style={{ backgroundColor: p.color, opacity: isOnline(p) ? 1 : 0.3 }}
                />
                <span className="text-sm" style={{ color: p.color }}>
                  {p.name}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen relative">
      <div className="paper-texture absolute inset-0 z-0" />

      {/* Hidden input for keyboard */}
      <input
        ref={inputRef}
        data-testid="hidden-input"
        value=""
        onChange={(e) => handleLetter(e.target.value)}
        onKeyDown={onKeyDown}
        autoComplete="off"
        autoCapitalize="characters"
        className="fixed opacity-0 pointer-events-none"
        style={{ top: 0, left: 0, width: 1, height: 1 }}
      />

      {/* Header */}
      <header className="sticky top-0 z-30 bg-[#f9f6f0] border-b border-[#d6cec2]">
        <div className="max-w-7xl mx-auto px-5 sm:px-8 h-16 flex items-center justify-between gap-4">
          <button
            data-testid="home-button"
            onClick={() => nav("/")}
            className="flex items-center gap-2 text-[#5c5856] hover:text-[#2c2a29] transition-colors"
          >
            <Home size={18} />
            <span className="font-serif text-xl hidden sm:inline">Cruciverba Insieme</span>
          </button>

          <div className="flex items-center gap-3 sm:gap-5">
            <div className="flex items-center gap-3" data-testid="presence">
              {players.map((p) => (
                <div key={p.id} className="flex items-center gap-1.5" title={p.name}>
                  <span
                    className="w-2.5 h-2.5 rounded-full"
                    style={{
                      backgroundColor: p.color,
                      opacity: isOnline(p) ? 1 : 0.3,
                    }}
                  />
                  <span
                    className="text-sm text-[#5c5856] max-w-[90px] truncate"
                    style={{ color: p.color }}
                  >
                    {p.name}
                  </span>
                </div>
              ))}
              {players.length < 2 && (
                <span className="text-xs text-[#8a8481] italic hidden sm:inline">
                  in attesa dell'altro giocatore…
                </span>
              )}
            </div>

            <button
              data-testid="share-button"
              onClick={share}
              className="flex items-center gap-2 rounded-full border border-[#d6cec2] hover:border-[#c05c48] px-4 py-1.5 transition-colors"
            >
              <span className="font-mono tracking-[0.3em] text-[#2c2a29]">{code}</span>
              <Share2 size={15} className="text-[#c05c48]" />
            </button>
          </div>
        </div>
      </header>

      {/* Body */}
      <main className="relative z-10 max-w-7xl mx-auto px-4 sm:px-8 py-8 grid lg:grid-cols-12 gap-8 lg:gap-12">
        <section className="lg:col-span-7 xl:col-span-8 flex flex-col items-center">
          {/* active clue banner */}
          {activeClue && (
            <div
              className="w-full mb-5 rounded-md bg-[#ffffff] border border-[#d6cec2] px-5 py-3 flex items-baseline gap-3"
              style={{ boxShadow: "inset 4px 0 0 0 var(--p2)" }}
              data-testid="active-clue-banner"
            >
              <span className="font-mono text-sm text-[#8a8481] shrink-0">
                {activeClue.num} {direction === "across" ? "Oriz." : "Vert."}
              </span>
              <span className="text-[#2c2a29] leading-snug">{activeClue.clue}</span>
            </div>
          )}
          <CrosswordGrid
            puzzle={puzzle}
            entries={entries}
            numberMap={numberMap}
            cellSet={cellSet}
            selected={selected}
            activeKeys={activeKeys}
            otherFocusKey={otherFocusKey}
            otherColor={other?.color || "#c05c48"}
            playersById={playersById}
            myColor={player.color}
            onCellClick={onCellClick}
            poppedKey={poppedKey}
          />
          <p className="mt-5 text-xs text-[#8a8481] text-center max-w-md">
            Clicca una casella e scrivi. Barra spaziatrice per cambiare direzione, frecce per
            muoverti. Ogni lettera appare in tempo reale all'altro giocatore.
          </p>
        </section>

        <aside className="lg:col-span-5 xl:col-span-4">
          <div className="lg:sticky lg:top-24 lg:max-h-[calc(100vh-8rem)]">
            <CluePanel
              puzzle={puzzle}
              activeNum={activeClue?.num}
              activeDir={direction}
              onSelect={selectClue}
            />
          </div>
        </aside>
      </main>

      {/* Victory overlay */}
      {status === "completed" && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-6 bg-[#2c2a29]/45 fade-up">
          <div className="bg-[#f9f6f0] rounded-lg border border-[#d6cec2] max-w-md w-full p-10 text-center">
            <PartyPopper className="mx-auto text-[#c05c48]" size={40} />
            <h2 className="font-serif text-4xl text-[#2c2a29] mt-4">Completato!</h2>
            <p className="text-[#5c5856] mt-3 leading-relaxed">
              Avete risolto il cruciverba insieme, a migliaia di chilometri di distanza. Bravi!
            </p>
            <button
              data-testid="new-puzzle-button"
              onClick={startNew}
              className="mt-8 inline-flex items-center gap-2 rounded-full bg-[#2c2a29] hover:bg-[#5c5856] text-[#f9f6f0] px-7 py-3 text-sm transition-colors"
            >
              <Sparkles size={16} />
              Nuovo cruciverba
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
