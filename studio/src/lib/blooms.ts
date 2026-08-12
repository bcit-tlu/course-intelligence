// Bloom's taxonomy level metadata: canonical order + color classes.
// Colors follow the Step 7 spec (Remember gray … Create purple).

export const BLOOMS_ORDER = [
  "Remember",
  "Understand",
  "Apply",
  "Analyze",
  "Evaluate",
  "Create",
] as const;

export type BloomsLevel = (typeof BLOOMS_ORDER)[number];

export const UNCLASSIFIED = "unclassified";

interface LevelStyle {
  badge: string; // badge bg/text/border classes
  bar: string; // solid fill for the distribution bar
}

const STYLES: Record<string, LevelStyle> = {
  Remember: { badge: "bg-slate-100 text-slate-700 border-slate-200", bar: "bg-slate-400" },
  Understand: { badge: "bg-blue-100 text-blue-700 border-blue-200", bar: "bg-blue-500" },
  Apply: { badge: "bg-green-100 text-green-700 border-green-200", bar: "bg-green-500" },
  Analyze: { badge: "bg-yellow-100 text-yellow-800 border-yellow-200", bar: "bg-yellow-500" },
  Evaluate: { badge: "bg-orange-100 text-orange-700 border-orange-200", bar: "bg-orange-500" },
  Create: { badge: "bg-purple-100 text-purple-700 border-purple-200", bar: "bg-purple-500" },
};

const UNCLASSIFIED_STYLE: LevelStyle = {
  badge: "bg-muted text-muted-foreground border-border",
  bar: "bg-muted-foreground/40",
};

export function normalizeLevel(level: string | null | undefined): string {
  if (!level) return UNCLASSIFIED;
  const match = BLOOMS_ORDER.find((l) => l.toLowerCase() === level.toLowerCase());
  return match ?? UNCLASSIFIED;
}

export function levelStyle(level: string): LevelStyle {
  return STYLES[level] ?? UNCLASSIFIED_STYLE;
}

/** All levels present in the data, in canonical order (unclassified last). */
export function levelsInOrder(present: Set<string>): string[] {
  const ordered = BLOOMS_ORDER.filter((l) => present.has(l)) as string[];
  if (present.has(UNCLASSIFIED)) ordered.push(UNCLASSIFIED);
  return ordered;
}
