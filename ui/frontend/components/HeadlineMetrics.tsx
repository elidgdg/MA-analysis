import { Minus, TrendingDown, TrendingUp } from "lucide-react";
import { Card } from "./ui/card";
import { cn } from "../lib/utils";
import {
  deltaNum,
  deltaPp,
  formatNumber,
  formatPct,
  toneClasses,
  type Tone,
} from "../lib/format";

type Props = {
  headline: {
    pending_announcement_jump: number | null;
    analogue_median_announcement_jump: number | null;
    pending_latest_spread_abs: number | null;
    analogue_median_latest_spread_abs_same_day: number | null;
    pending_day_5_return?: number | null;
    analogue_median_day_5_return?: number | null;
  };
};

const TONE_ICON: Record<Tone, typeof TrendingUp> = {
  positive: TrendingUp,
  negative: TrendingDown,
  neutral: Minus,
};

type CardConfig = {
  label: string;
  hint: string;
  pending: number | null | undefined;
  cohort: number | null | undefined;
  pendingDisplay: string;
  cohortDisplay: string;
  delta: { text: string; tone: Tone } | null;
};

function DeltaChip({ delta }: { delta: { text: string; tone: Tone } }) {
  const Icon = TONE_ICON[delta.tone];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold tabular-nums ring-1 ring-inset",
        toneClasses[delta.tone]
      )}
    >
      <Icon className="h-3 w-3" aria-hidden />
      {delta.text}
    </span>
  );
}

function MetricCard({ config }: { config: CardConfig }) {
  return (
    <Card className="group relative overflow-hidden p-5 transition-all hover:shadow-md">
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-border to-transparent" />

      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
            {config.label}
          </div>
          <div className="mt-0.5 text-xs text-muted-foreground/80">
            {config.hint}
          </div>
        </div>
        {config.delta && <DeltaChip delta={config.delta} />}
      </div>

      <div className="mt-4 flex items-baseline gap-2">
        <span className="font-mono text-3xl font-semibold tabular-nums tracking-tight">
          {config.pendingDisplay}
        </span>
        <span className="text-xs font-medium uppercase tracking-wider text-accent">
          Pending
        </span>
      </div>

      <div className="mt-3 flex items-center justify-between border-t pt-3 text-xs">
        <span className="text-muted-foreground">Cohort median</span>
        <span className="font-mono font-medium tabular-nums text-foreground/80">
          {config.cohortDisplay}
        </span>
      </div>
    </Card>
  );
}

export default function HeadlineMetrics({ headline }: Props) {
  const cards: CardConfig[] = [
    {
      label: "Announcement jump",
      hint: "Day-0 reaction",
      pending: headline.pending_announcement_jump,
      cohort: headline.analogue_median_announcement_jump,
      pendingDisplay: formatPct(headline.pending_announcement_jump, { signed: true }),
      cohortDisplay: formatPct(headline.analogue_median_announcement_jump, { signed: true }),
      delta: deltaPp(
        headline.pending_announcement_jump,
        headline.analogue_median_announcement_jump
      ),
    },
    {
      label: "Day-5 return",
      hint: "Cumulative through day 5",
      pending: headline.pending_day_5_return ?? null,
      cohort: headline.analogue_median_day_5_return ?? null,
      pendingDisplay: formatPct(headline.pending_day_5_return ?? null, { signed: true }),
      cohortDisplay: formatPct(headline.analogue_median_day_5_return ?? null, { signed: true }),
      delta: deltaPp(
        headline.pending_day_5_return ?? null,
        headline.analogue_median_day_5_return ?? null
      ),
    },
    {
      label: "Latest spread",
      hint: "Current vs offer",
      pending: headline.pending_latest_spread_abs,
      cohort: headline.analogue_median_latest_spread_abs_same_day,
      pendingDisplay: formatNumber(headline.pending_latest_spread_abs, { digits: 4 }),
      cohortDisplay: formatNumber(headline.analogue_median_latest_spread_abs_same_day, { digits: 4 }),
      delta: deltaNum(
        headline.pending_latest_spread_abs,
        headline.analogue_median_latest_spread_abs_same_day,
        4,
        0.0005
      ),
    },
  ].filter((card) => card.pending !== null && card.pending !== undefined ||
                     card.cohort !== null && card.cohort !== undefined);

  if (cards.length === 0) return null;

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
      {cards.map((card) => (
        <MetricCard key={card.label} config={card} />
      ))}
    </div>
  );
}
