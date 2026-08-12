import { useState } from "react";
import { ChevronDown, FileText } from "lucide-react";

import BloomsBadge from "@/components/BloomsBadge";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { LearningElement } from "@/types";

const COLLAPSE_THRESHOLD = 280; // chars before we offer a "show more" toggle

export default function ElementCard({ element }: { element: LearningElement }) {
  const [expanded, setExpanded] = useState(false);
  const isLong = element.content.length > COLLAPSE_THRESHOLD;

  const pageRef =
    element.source_page ??
    (element.page_number != null ? `Page ${element.page_number}` : null);

  return (
    <Card>
      <CardContent className="space-y-3 p-5">
        <div className="flex items-start justify-between gap-3">
          <h3 className="font-semibold leading-tight">{element.topic}</h3>
          <BloomsBadge level={element.blooms_level} className="shrink-0" />
        </div>

        <p
          className={cn(
            "text-sm text-foreground/80",
            isLong && !expanded && "line-clamp-3",
          )}
        >
          {element.content}
        </p>

        {isLong && (
          <button
            onClick={() => setExpanded((v) => !v)}
            className="flex items-center gap-1 text-xs font-medium text-primary hover:underline"
          >
            {expanded ? "Show less" : "Show more"}
            <ChevronDown
              className={cn(
                "h-3.5 w-3.5 transition-transform",
                expanded && "rotate-180",
              )}
            />
          </button>
        )}

        {element.blooms_rationale && (
          <p className="border-l-2 border-border pl-3 text-xs italic text-muted-foreground">
            {element.blooms_rationale}
          </p>
        )}

        {pageRef && (
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <FileText className="h-3.5 w-3.5" />
            <span>{pageRef}</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
