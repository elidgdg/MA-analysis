export type Tone = "positive" | "negative" | "neutral";

const NA = "—";

export function isNumber(value: unknown): value is number {
  return typeof value === "number" && !Number.isNaN(value);
}

/** Render a decimal as a percentage (0.042 → "4.20%"). */
export function formatPct(
  value: number | null | undefined,
  opts: { signed?: boolean; digits?: number } = {}
): string {
  if (!isNumber(value)) return NA;
  const digits = opts.digits ?? 2;
  const pct = value * 100;
  const formatted = pct.toFixed(digits);
  if (opts.signed && pct > 0) return `+${formatted}%`;
  return `${formatted}%`;
}

/** Render a plain number with optional sign. */
export function formatNumber(
  value: number | null | undefined,
  opts: { signed?: boolean; digits?: number } = {}
): string {
  if (!isNumber(value)) return NA;
  const digits = opts.digits ?? 2;
  const formatted = value.toFixed(digits);
  if (opts.signed && value > 0) return `+${formatted}`;
  return formatted;
}

/** Render a multiplier ratio (1.5 → "1.50×"). */
export function formatRatio(value: number | null | undefined, digits = 2): string {
  if (!isNumber(value)) return NA;
  return `${value.toFixed(digits)}×`;
}

/** Render a USD value in millions (e.g. 1234 → "$1.23B", 250 → "$250M"). */
export function formatUSDMil(value: number | null | undefined): string {
  if (!isNumber(value)) return NA;
  if (Math.abs(value) >= 1000) return `$${(value / 1000).toFixed(2)}B`;
  return `$${value.toFixed(0)}M`;
}

/** Format an ISO date string as "May 7, 2026". Falls back to slice(0,10). */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return NA;
  const trimmed = iso.length > 10 ? iso.slice(0, 10) : iso;
  const d = new Date(trimmed);
  if (Number.isNaN(d.getTime())) return trimmed;
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  }).format(d);
}

/** Format an event-day index (-5 → "-5", 0 → "0", 5 → "+5"). */
export function formatEventDay(day: number): string {
  if (day === 0) return "0";
  if (day > 0) return `+${day}`;
  return `${day}`;
}

function classifyTone(diff: number, threshold: number): Tone {
  if (Math.abs(diff) < threshold) return "neutral";
  return diff > 0 ? "positive" : "negative";
}

/** Pending - analogue, formatted as percentage points. */
export function deltaPp(
  pending: number | null | undefined,
  analogue: number | null | undefined,
  threshold = 0.005
): { text: string; tone: Tone } | null {
  if (!isNumber(pending) || !isNumber(analogue)) return null;
  const diff = pending - analogue;
  const tone = classifyTone(diff, threshold);
  const sign = diff > 0 ? "+" : "";
  return { text: `${sign}${(diff * 100).toFixed(2)}pp`, tone };
}

/** Pending - analogue, formatted as a plain delta. */
export function deltaNum(
  pending: number | null | undefined,
  analogue: number | null | undefined,
  digits = 2,
  threshold = 0.005
): { text: string; tone: Tone } | null {
  if (!isNumber(pending) || !isNumber(analogue)) return null;
  const diff = pending - analogue;
  const tone = classifyTone(diff, threshold);
  const sign = diff > 0 ? "+" : "";
  return { text: `${sign}${diff.toFixed(digits)}`, tone };
}

export const toneClasses: Record<Tone, string> = {
  positive: "bg-success/10 text-success ring-success/20",
  negative: "bg-destructive/10 text-destructive ring-destructive/20",
  neutral: "bg-muted text-muted-foreground ring-border",
};
