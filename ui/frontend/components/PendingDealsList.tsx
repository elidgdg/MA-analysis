"use client";

import * as React from "react";
import { Search, X } from "lucide-react";
import { cn } from "../lib/utils";
import { formatDate } from "../lib/format";

type PendingDeal = {
  event_id: number;
  target_name: string;
  acquirer_name: string | null;
  announcement_date: string | null;
  expected_completion_date: string | null;
  payment_type: string | null;
  target_sector: string | null;
};

type Props = {
  deals: PendingDeal[];
  selectedEventId: number;
};

function matches(deal: PendingDeal, q: string): boolean {
  if (!q) return true;
  const needle = q.toLowerCase();
  return (
    deal.target_name.toLowerCase().includes(needle) ||
    (deal.acquirer_name?.toLowerCase().includes(needle) ?? false) ||
    (deal.target_sector?.toLowerCase().includes(needle) ?? false)
  );
}

export default function PendingDealsList({ deals, selectedEventId }: Props) {
  const [query, setQuery] = React.useState("");
  const filtered = React.useMemo(
    () => deals.filter((d) => matches(d, query)),
    [deals, query]
  );

  return (
    <aside className="rounded-2xl border bg-card shadow-sm lg:sticky lg:top-[80px] lg:max-h-[calc(100vh-6rem)] lg:overflow-hidden">
      <div className="flex flex-col gap-3 border-b px-4 py-4">
        <div className="flex items-baseline justify-between">
          <h2 className="text-sm font-semibold tracking-tight">Pending deals</h2>
          <span className="font-mono text-[11px] tabular-nums text-muted-foreground">
            {query ? `${filtered.length}/${deals.length}` : `${deals.length}`}
          </span>
        </div>

        <div className="relative">
          <Search
            className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground"
            aria-hidden
          />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search target, acquirer, sector…"
            aria-label="Search pending deals"
            className={cn(
              "h-8 w-full rounded-lg border bg-background pl-8 pr-7 text-xs",
              "placeholder:text-muted-foreground",
              "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1 focus:ring-offset-background"
            )}
          />
          {query && (
            <button
              type="button"
              onClick={() => setQuery("")}
              aria-label="Clear search"
              className="absolute right-1.5 top-1/2 flex h-5 w-5 -translate-y-1/2 items-center justify-center rounded text-muted-foreground hover:bg-muted hover:text-foreground"
            >
              <X className="h-3 w-3" aria-hidden />
            </button>
          )}
        </div>
      </div>

      <nav className="flex max-h-[calc(100vh-13rem)] flex-col gap-1 overflow-y-auto p-2">
        {filtered.length === 0 ? (
          <div className="px-3 py-8 text-center text-xs text-muted-foreground">
            No deals match “{query}”.
          </div>
        ) : (
          filtered.map((deal) => {
            const selected = deal.event_id === selectedEventId;

            return (
              <a
                key={deal.event_id}
                href={`/?event_id=${deal.event_id}`}
                aria-current={selected ? "page" : undefined}
                className={cn(
                  "group relative flex flex-col gap-1 rounded-xl border border-transparent px-3 py-3 text-left transition-all",
                  "hover:border-border hover:bg-muted/40",
                  selected && "border-border bg-muted/60 shadow-sm"
                )}
              >
                <span
                  className={cn(
                    "absolute inset-y-2 left-0 w-0.5 rounded-full bg-accent transition-opacity",
                    selected ? "opacity-100" : "opacity-0"
                  )}
                  aria-hidden
                />

                <div
                  className={cn(
                    "truncate text-sm font-semibold transition-colors",
                    selected ? "text-foreground" : "text-foreground/90"
                  )}
                >
                  {deal.target_name}
                </div>

                <div className="truncate text-xs text-muted-foreground">
                  {deal.acquirer_name ?? "Unknown acquirer"}
                </div>

                <div className="mt-1 flex flex-wrap items-center gap-1.5 text-[11px] text-muted-foreground">
                  {deal.payment_type && (
                    <span className="rounded-md bg-secondary px-1.5 py-0.5 font-medium text-secondary-foreground">
                      {deal.payment_type}
                    </span>
                  )}
                  {deal.target_sector && (
                    <span className="truncate">{deal.target_sector}</span>
                  )}
                </div>

                {deal.announcement_date && (
                  <div className="text-[11px] tabular-nums text-muted-foreground/80">
                    {formatDate(deal.announcement_date)}
                  </div>
                )}
              </a>
            );
          })
        )}
      </nav>
    </aside>
  );
}
