import { useMemo } from "react";

export default function CrosswordGrid({
  puzzle,
  entries,
  numberMap,
  cellSet,
  selected,
  activeKeys,
  otherFocusKey,
  otherColor,
  playersById,
  myColor,
  onCellClick,
  poppedKey,
}) {
  const size = puzzle.size;
  const GW = "min(92vw, 680px)";
  const letterSize = `calc(${GW} / ${size} * 0.56)`;
  const numberSize = `calc(${GW} / ${size} * 0.26)`;
  const cells = useMemo(() => {
    const rows = [];
    for (let r = 0; r < size; r++) {
      const row = [];
      for (let c = 0; c < size; c++) row.push(`${r}-${c}`);
      rows.push(row);
    }
    return rows;
  }, [size]);

  return (
    <div
      className="w-full mx-auto select-none"
      style={{ maxWidth: GW }}
      data-testid="crossword-grid"
    >
      <div
        className="grid gap-[1px] bg-[#2c2a29] p-[1px] rounded-sm"
        style={{ gridTemplateColumns: `repeat(${size}, 1fr)` }}
      >
        {cells.flat().map((key) => {
          const [r, c] = key.split("-").map(Number);
          const isCell = cellSet.has(key);
          if (!isCell) {
            return <div key={key} className="aspect-square bg-[#2c2a29]" />;
          }
          const entry = entries[key];
          const letter = entry?.letter || "";
          const letterColor = entry ? playersById[entry.playerId]?.color || "#2c2a29" : "#2c2a29";
          const isSelected = selected && selected.row === r && selected.col === c;
          const inActive = activeKeys.has(key);
          const num = numberMap[key];
          const showOther = otherFocusKey === key;

          let bg = "#ffffff";
          if (inActive) bg = "#eae4d9";
          if (isSelected) bg = "#dcd4c4";

          return (
            <button
              key={key}
              data-testid={`cell-${r}-${c}`}
              onClick={() => onCellClick(r, c)}
              className="relative aspect-square flex items-center justify-center transition-colors"
              style={{
                backgroundColor: bg,
                boxShadow: isSelected ? `inset 0 0 0 2px ${myColor}` : "none",
              }}
            >
              {num != null && (
                <span
                  className="absolute top-[1px] left-[2px] font-mono leading-none text-[#8a8481]"
                  style={{ fontSize: numberSize }}
                >
                  {num}
                </span>
              )}
              {showOther && (
                <span
                  className="absolute top-0 right-0 w-0 h-0"
                  style={{
                    borderTop: `9px solid ${otherColor}`,
                    borderLeft: "9px solid transparent",
                  }}
                />
              )}
              <span
                className={`font-mono font-medium ${poppedKey === key ? "cell-pop" : ""}`}
                style={{ color: letterColor, fontSize: letterSize }}
              >
                {letter}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
