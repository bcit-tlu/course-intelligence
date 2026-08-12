import { Badge } from "@/components/ui/badge";
import { levelStyle, normalizeLevel } from "@/lib/blooms";
import { cn } from "@/lib/utils";

export default function BloomsBadge({
  level,
  className,
}: {
  level: string | null;
  className?: string;
}) {
  const normalized = normalizeLevel(level);
  const label = normalized === "unclassified" ? "Unclassified" : normalized;
  return (
    <Badge className={cn(levelStyle(normalized).badge, className)}>
      {label}
    </Badge>
  );
}
