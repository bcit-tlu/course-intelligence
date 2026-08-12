import { levelStyle, levelsInOrder, normalizeLevel } from "@/lib/blooms";
import { cn } from "@/lib/utils";
import type { LearningElement } from "@/types";

export function countByLevel(elements: LearningElement[]): Map<string, number> {
  const counts = new Map<string, number>();
  for (const el of elements) {
    const level = normalizeLevel(el.blooms_level);
    counts.set(level, (counts.get(level) ?? 0) + 1);
  }
  return counts;
}

export default function BloomsSummary({
  elements,
}: {
  elements: LearningElement[];
}) {
  const counts = countByLevel(elements);
  const total = elements.length;
  const levels = levelsInOrder(new Set(counts.keys()));

  if (total === 0) return null;

  return (
    <div className="space-y-3">
      {/* Stacked distribution bar */}
      <div className="flex h-2.5 w-full overflow-hidden rounded-full bg-secondary">
        {levels.map((level) => {
          const pct = ((counts.get(level) ?? 0) / total) * 100;
          return (
            <div
              key={level}
              className={cn("h-full", levelStyle(level).bar)}
              style={{ width: `${pct}%` }}
              title={`${level}: ${counts.get(level)}`}
            />
          );
        })}
      </div>

      {/* Legend with counts */}
      <div className="flex flex-wrap gap-x-4 gap-y-1">
        {levels.map((level) => (
          <div key={level} className="flex items-center gap-1.5 text-sm">
            <span
              className={cn(
                "inline-block h-2.5 w-2.5 rounded-full",
                levelStyle(level).bar,
              )}
            />
            <span className="capitalize text-muted-foreground">
              {level === "unclassified" ? "Unclassified" : level}
            </span>
            <span className="font-medium">{counts.get(level)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
