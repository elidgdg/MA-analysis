"use client";

import * as React from "react";
import { ChevronDown, ChevronUp, ChevronsUpDown } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "./ui/card";
import { Badge } from "./ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "./ui/table";
import { cn } from "../lib/utils";
import { formatDate } from "../lib/format";

type Analogue = {
  event_id: number;
  target_name: string;
  announcement_date: string | null;
  tier: number;
  score: number;
  reasons: string[];
};

type Props = {
  analogues: Analogue[];
};

type SortKey = "rank" | "target" | "tier" | "date" | "score";
type SortDir = "asc" | "desc";

const DEFAULT_DIR: Record<SortKey, SortDir> = {
  rank: "asc",
  target: "asc",
  tier: "asc",
  date: "desc",
  score: "desc",
};

function tierMeta(tier: number): { label: string; variant: "default" | "secondary" | "muted" } {
  if (tier === 1) return { label: "Tier 1", variant: "default" };
  if (tier === 2) return { label: "Tier 2", variant: "secondary" };
  return { label: `Tier ${tier}`, variant: "muted" };
}

function ScoreBar({ score }: { score: number }) {
  const pct = Math.max(0, Math.min(1, score)) * 100;
  return (
    <div className="flex items-center gap-2.5">
      <div className="relative h-1.5 w-20 overflow-hidden rounded-full bg-muted">
        <div
          className="absolute inset-y-0 left-0 rounded-full bg-accent"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="font-mono text-xs tabular-nums text-muted-foreground">
        {score.toFixed(2)}
      </span>
    </div>
  );
}

function SortIcon({ active, dir }: { active: boolean; dir: SortDir }) {
  if (!active) {
    return (
      <ChevronsUpDown
        className="h-3 w-3 text-muted-foreground/50 transition-colors group-hover:text-muted-foreground"
        aria-hidden
      />
    );
  }
  return dir === "asc" ? (
    <ChevronUp className="h-3 w-3 text-foreground" aria-hidden />
  ) : (
    <ChevronDown className="h-3 w-3 text-foreground" aria-hidden />
  );
}

function HeaderButton({
  label,
  sortKey,
  active,
  dir,
  onClick,
  className,
}: {
  label: string;
  sortKey: SortKey;
  active: boolean;
  dir: SortDir;
  onClick: (key: SortKey) => void;
  className?: string;
}) {
  return (
    <button
      type="button"
      onClick={() => onClick(sortKey)}
      aria-sort={active ? (dir === "asc" ? "ascending" : "descending") : "none"}
      className={cn(
        "group inline-flex items-center gap-1.5 text-xs font-medium uppercase tracking-wider transition-colors",
        active ? "text-foreground" : "text-muted-foreground hover:text-foreground",
        className
      )}
    >
      <span>{label}</span>
      <SortIcon active={active} dir={dir} />
    </button>
  );
}

export default function AnalogueTable({ analogues }: Props) {
  const [sortKey, setSortKey] = React.useState<SortKey>("rank");
  const [sortDir, setSortDir] = React.useState<SortDir>("asc");

  const handleSort = React.useCallback(
    (key: SortKey) => {
      if (key === sortKey) {
        setSortDir((d) => (d === "asc" ? "desc" : "asc"));
      } else {
        setSortKey(key);
        setSortDir(DEFAULT_DIR[key]);
      }
    },
    [sortKey]
  );

  const ranked = React.useMemo(
    () => analogues.map((item, idx) => ({ item, originalRank: idx + 1 })),
    [analogues]
  );

  const sorted = React.useMemo(() => {
    const dir = sortDir === "asc" ? 1 : -1;
    const copy = [...ranked];
    copy.sort((a, b) => {
      switch (sortKey) {
        case "rank":
          return (a.originalRank - b.originalRank) * dir;
        case "tier":
          return (a.item.tier - b.item.tier) * dir || a.originalRank - b.originalRank;
        case "score":
          return (a.item.score - b.item.score) * dir;
        case "target":
          return a.item.target_name.localeCompare(b.item.target_name) * dir;
        case "date": {
          const av = a.item.announcement_date ?? "";
          const bv = b.item.announcement_date ?? "";
          if (av === bv) return 0;
          return (av < bv ? -1 : 1) * dir;
        }
        default:
          return 0;
      }
    });
    return copy;
  }, [ranked, sortKey, sortDir]);

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <div>
          <CardTitle>Top analogues</CardTitle>
          <CardDescription>
            Ranked by similarity to the pending deal · click headers to sort
          </CardDescription>
        </div>
        <Badge variant="muted">{analogues.length} matches</Badge>
      </CardHeader>

      <CardContent className="px-0 pb-0">
        {analogues.length === 0 ? (
          <div className="px-6 pb-6 text-sm text-muted-foreground">
            No analogues matched for this deal yet.
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead className="w-14 pl-6">
                  <HeaderButton
                    label="#"
                    sortKey="rank"
                    active={sortKey === "rank"}
                    dir={sortDir}
                    onClick={handleSort}
                  />
                </TableHead>
                <TableHead>
                  <HeaderButton
                    label="Target"
                    sortKey="target"
                    active={sortKey === "target"}
                    dir={sortDir}
                    onClick={handleSort}
                  />
                </TableHead>
                <TableHead className="w-24">
                  <HeaderButton
                    label="Tier"
                    sortKey="tier"
                    active={sortKey === "tier"}
                    dir={sortDir}
                    onClick={handleSort}
                  />
                </TableHead>
                <TableHead className="w-36">
                  <HeaderButton
                    label="Date"
                    sortKey="date"
                    active={sortKey === "date"}
                    dir={sortDir}
                    onClick={handleSort}
                  />
                </TableHead>
                <TableHead className="w-40">
                  <HeaderButton
                    label="Score"
                    sortKey="score"
                    active={sortKey === "score"}
                    dir={sortDir}
                    onClick={handleSort}
                  />
                </TableHead>
                <TableHead className="pr-6 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Reasons
                </TableHead>
              </TableRow>
            </TableHeader>

            <TableBody>
              {sorted.map(({ item, originalRank }) => {
                const tier = tierMeta(item.tier);
                return (
                  <TableRow key={item.event_id}>
                    <TableCell className="pl-6 font-mono text-xs tabular-nums text-muted-foreground">
                      {String(originalRank).padStart(2, "0")}
                    </TableCell>
                    <TableCell className="font-medium">{item.target_name}</TableCell>
                    <TableCell>
                      <Badge variant={tier.variant}>{tier.label}</Badge>
                    </TableCell>
                    <TableCell className="text-xs tabular-nums text-muted-foreground">
                      {formatDate(item.announcement_date)}
                    </TableCell>
                    <TableCell>
                      <ScoreBar score={item.score} />
                    </TableCell>
                    <TableCell className="pr-6">
                      {Array.isArray(item.reasons) && item.reasons.length > 0 ? (
                        <div className="flex flex-wrap gap-1">
                          {item.reasons.map((reason, i) => (
                            <span
                              key={i}
                              className={cn(
                                "rounded-md border bg-muted/50 px-1.5 py-0.5 text-[11px]",
                                "text-muted-foreground"
                              )}
                            >
                              {reason}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
