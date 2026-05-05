type HeadlineComparison = {
  pending_announcement_jump: number | null;
  analogue_median_announcement_jump: number | null;
  pending_day_5_return?: number | null;
  analogue_median_day_5_return?: number | null;
  pending_latest_spread_abs: number | null;
  analogue_median_latest_spread_abs_same_day: number | null;
  pending_latest_spread_pct?: number | null;
  analogue_median_latest_spread_pct_same_day?: number | null;
};

type AnalogueSelection = {
  tier_1_same_sector_count: number;
  tier_2_fallback_count: number;
};

type Props = {
  headline: HeadlineComparison;
  analogueSelection: AnalogueSelection;
};

function fmtPct(value: number | null | undefined) {
  if (value === null || value === undefined) return "N/A";
  return `${(value * 100).toFixed(1)}%`;
}

function fmtNum(value: number | null | undefined) {
  if (value === null || value === undefined) return "N/A";
  return value.toFixed(2);
}

function classifyDifference(
  pending: number | null | undefined,
  analogue: number | null | undefined,
  higherWord: string,
  lowerWord: string
) {
  if (pending === null || pending === undefined || analogue === null || analogue === undefined) {
    return null;
  }

  const diff = pending - analogue;
  const absDiff = Math.abs(diff);

  if (absDiff < 0.01) return "broadly in line";

  if (diff > 0) {
    if (absDiff > 0.08) return `materially ${higherWord}`;
    if (absDiff > 0.03) return `${higherWord}`;
    return `slightly ${higherWord}`;
  }

  if (absDiff > 0.08) return `materially ${lowerWord}`;
  if (absDiff > 0.03) return `${lowerWord}`;
  return `slightly ${lowerWord}`;
}

export default function InsightCommentary({
  headline,
  analogueSelection,
}: Props) {
  const announcementView = classifyDifference(
    headline.pending_announcement_jump,
    headline.analogue_median_announcement_jump,
    "stronger",
    "weaker"
  );

  const day5View = classifyDifference(
    headline.pending_day_5_return,
    headline.analogue_median_day_5_return,
    "stronger",
    "weaker"
  );

  const spreadView = classifyDifference(
    headline.pending_latest_spread_abs,
    headline.analogue_median_latest_spread_abs_same_day,
    "wider",
    "narrower"
  );

  const tier1 = analogueSelection.tier_1_same_sector_count;
  const tier2 = analogueSelection.tier_2_fallback_count;

  const bullets: string[] = [];

  if (announcementView) {
    bullets.push(
      `The pending deal's announcement reaction looks ${announcementView} than the analogue median (${fmtPct(
        headline.pending_announcement_jump
      )} vs ${fmtPct(headline.analogue_median_announcement_jump)}).`
    );
  }

  if (day5View) {
    bullets.push(
      `By day 5, the pending deal still looks ${day5View} than analogue history (${fmtPct(
        headline.pending_day_5_return
      )} vs ${fmtPct(headline.analogue_median_day_5_return)}).`
    );
  }

  if (spreadView) {
    bullets.push(
      `At the current comparison horizon, the spread is ${spreadView} than the analogue median (${fmtNum(
        headline.pending_latest_spread_abs
      )} vs ${fmtNum(headline.analogue_median_latest_spread_abs_same_day)}).`
    );
  }

  bullets.push(
    `Analogue coverage includes ${tier1} same-sector analogue${tier1 === 1 ? "" : "s"} and ${tier2} fallback analogue${tier2 === 1 ? "" : "s"}, so the strongest comparisons should generally come from the same-sector names first.`
  );

  return (
    <div
      style={{
        background: "white",
        border: "1px solid #e2e8f0",
        borderRadius: "16px",
        padding: "20px",
      }}
    >
      <h3 style={{ marginTop: 0, marginBottom: "12px" }}>Interpretation</h3>

      <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
        {bullets.map((bullet, idx) => (
          <div
            key={idx}
            style={{
              padding: "12px 14px",
              borderRadius: "12px",
              background: "#f8fafc",
              border: "1px solid #e2e8f0",
              color: "#334155",
              lineHeight: 1.5,
            }}
          >
            {bullet}
          </div>
        ))}
      </div>
    </div>
  );
}