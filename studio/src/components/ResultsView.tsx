import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Plus, SearchX } from "lucide-react";

import BloomsSummary, { countByLevel } from "@/components/BloomsSummary";
import ElementCard from "@/components/ElementCard";
import LevelFilter from "@/components/LevelFilter";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { levelsInOrder, normalizeLevel } from "@/lib/blooms";
import type { JobResults } from "@/types";

export default function ResultsView({ results }: { results: JobResults }) {
  const [activeLevel, setActiveLevel] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  const { elements } = results;
  const counts = useMemo(() => countByLevel(elements), [elements]);
  const levels = useMemo(
    () => levelsInOrder(new Set(counts.keys())),
    [counts],
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return elements.filter((el) => {
      const levelOk =
        activeLevel === null || normalizeLevel(el.blooms_level) === activeLevel;
      const queryOk =
        q === "" ||
        el.topic.toLowerCase().includes(q) ||
        el.content.toLowerCase().includes(q);
      return levelOk && queryOk;
    });
  }, [elements, activeLevel, query]);

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <CardTitle className="text-xl">{results.filename}</CardTitle>
              <CardDescription>
                {elements.length} learning{" "}
                {elements.length === 1 ? "element" : "elements"}
              </CardDescription>
            </div>
            <Button asChild variant="outline" size="sm">
              <Link to="/">
                <Plus className="h-4 w-4" />
                New upload
              </Link>
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <BloomsSummary elements={elements} />
        </CardContent>
      </Card>

      <LevelFilter
        levels={levels}
        counts={counts}
        active={activeLevel}
        onSelectLevel={setActiveLevel}
        query={query}
        onQueryChange={setQuery}
      />

      {filtered.length === 0 ? (
        <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed py-16 text-center text-muted-foreground">
          <SearchX className="h-8 w-8" />
          <p className="font-medium">No matching elements</p>
          <p className="text-sm">Try clearing the filter or search.</p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {filtered.map((el) => (
            <ElementCard key={el.id} element={el} />
          ))}
        </div>
      )}
    </div>
  );
}
