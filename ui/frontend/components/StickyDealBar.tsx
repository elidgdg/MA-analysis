"use client";

import * as React from "react";
import { Minus, TrendingDown, TrendingUp } from "lucide-react";
import { cn } from "../lib/utils";
import { deltaPp, formatPct, toneClasses, type Tone } from "../lib/format";

type Props = {
  targetName: string;
  acquirerName: string | null;
  pendingJump: number | null;
  cohortJump: number | null;
  sentinelId: string;
};

const TONE_ICON: Record<Tone, typeof TrendingUp> = {
  positive: TrendingUp,
  negative: TrendingDown,
  neutral: Minus,
};

export default function StickyDealBar({
  targetName,
  acquirerName,
  pendingJump,
  cohortJump,
  sentinelId,
}: Props) {
  const [visible, setVisible] = React.useState(false);

  React.useEffect(() => {
    const sentinel = document.getElementById(sentinelId);
    if (!sentinel || typeof IntersectionObserver === "undefined") return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        // Show the bar only when the sentinel (placed under the deal summary) is fully above the viewport
        setVisible(!entry.isIntersecting && entry.boundingClientRect.top < 0);
      },
      { threshold: 0, rootMargin: "0px 0px 0px 0px" }
    );

    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [sentinelId]);

  const delta = deltaPp(pendingJump, cohortJump);
  const Icon = delta ? TONE_ICON[delta.tone] : null;

  return (
    <div
      aria-hidden={!visible}
      className={cn(
        "pointer-events-none fixed inset-x-0 top-[64px] z-20 transition-all duration-200 ease-out",
        visible ? "translate-y-0 opacity-100" : "-translate-y-2 opacity-0"
      )}
    >
      <div
        className={cn(
          "border-b bg-background/85 backdrop-blur-md",
          visible && "pointer-events-auto"
        )}
      >
        <div className="mx-auto flex w-full max-w-[1480px] items-center gap-3 px-6 py-2.5">
          <div className="flex min-w-0 flex-1 items-center gap-2 text-sm">
            <span className="truncate font-semibold tracking-tight">{targetName}</span>
            <span className="text-muted-foreground" aria-hidden>
              ←
            </span>
            <span className="truncate text-muted-foreground">
              {acquirerName ?? "Unknown acquirer"}
            </span>
          </div>

          <div className="flex shrink-0 items-center gap-2 text-xs">
            <span className="hidden text-muted-foreground sm:inline">Announcement jump</span>
            <span className="font-mono font-semibold tabular-nums">
              {formatPct(pendingJump, { signed: true })}
            </span>
            {delta && Icon && (
              <span
                className={cn(
                  "inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[10px] font-semibold tabular-nums ring-1 ring-inset",
                  toneClasses[delta.tone]
                )}
              >
                <Icon className="h-3 w-3" aria-hidden />
                {delta.text}
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
