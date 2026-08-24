import { useEffect, useRef } from "react";

function ClueList({ title, clues, direction, activeNum, activeDir, onSelect }) {
  return (
    <div>
      <h3 className="font-serif text-2xl text-[#2c2a29] mb-3 flex items-baseline gap-2">
        {title}
        <span className="font-sans text-xs text-[#8a8481] tracking-widest uppercase">
          {clues.length}
        </span>
      </h3>
      <ul className="space-y-0.5">
        {clues.map((clue) => {
          const active = activeDir === direction && activeNum === clue.num;
          return (
            <li key={clue.num}>
              <button
                data-testid={`clue-${direction}-${clue.num}`}
                onClick={() => onSelect(clue, direction)}
                data-active={active}
                className={`w-full text-left flex gap-3 px-3 py-2 rounded-sm transition-colors ${
                  active ? "bg-[#eae4d9]" : "hover:bg-[#f2ede4]"
                }`}
                style={active ? { boxShadow: `inset 3px 0 0 0 var(--p2)` } : {}}
              >
                <span className="font-mono text-sm text-[#8a8481] w-6 shrink-0 pt-0.5">
                  {clue.num}
                </span>
                <span
                  className={`text-sm leading-snug ${
                    active ? "text-[#2c2a29]" : "text-[#5c5856]"
                  }`}
                >
                  {clue.clue}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export default function CluePanel({ puzzle, activeNum, activeDir, onSelect }) {
  const wrapRef = useRef(null);

  useEffect(() => {
    if (!wrapRef.current) return;
    const el = wrapRef.current.querySelector('[data-active="true"]');
    if (el) el.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [activeNum, activeDir]);

  return (
    <div ref={wrapRef} className="clue-scroll space-y-8 overflow-y-auto pr-2">
      <ClueList
        title="Orizzontali"
        clues={puzzle.across}
        direction="across"
        activeNum={activeNum}
        activeDir={activeDir}
        onSelect={onSelect}
      />
      <ClueList
        title="Verticali"
        clues={puzzle.down}
        direction="down"
        activeNum={activeNum}
        activeDir={activeDir}
        onSelect={onSelect}
      />
    </div>
  );
}
