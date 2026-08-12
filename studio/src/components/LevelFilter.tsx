import { Search } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { levelStyle } from "@/lib/blooms";
import { cn } from "@/lib/utils";

interface LevelFilterProps {
  levels: string[]; // levels present in the data, in order
  counts: Map<string, number>;
  active: string | null; // null = all
  onSelectLevel: (level: string | null) => void;
  query: string;
  onQueryChange: (q: string) => void;
}

export default function LevelFilter({
  levels,
  counts,
  active,
  onSelectLevel,
  query,
  onQueryChange,
}: LevelFilterProps) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex flex-wrap gap-2">
        <button onClick={() => onSelectLevel(null)}>
          <Badge
            className={cn(
              "cursor-pointer",
              active === null
                ? "border-primary bg-primary text-primary-foreground"
                : "bg-background hover:bg-accent",
            )}
          >
            All
          </Badge>
        </button>
        {levels.map((level) => {
          const isActive = active === level;
          const label = level === "unclassified" ? "Unclassified" : level;
          return (
            <button key={level} onClick={() => onSelectLevel(level)}>
              <Badge
                className={cn(
                  "cursor-pointer capitalize",
                  isActive
                    ? levelStyle(level).badge + " ring-2 ring-offset-1"
                    : "bg-background hover:bg-accent",
                )}
              >
                {label} ({counts.get(level) ?? 0})
              </Badge>
            </button>
          );
        })}
      </div>

      <div className="relative sm:w-64">
        <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search topics…"
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          className="pl-8"
        />
      </div>
    </div>
  );
}
