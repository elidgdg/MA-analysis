type Props = {
  headline: {
    pending_announcement_jump: number | null;
    analogue_median_announcement_jump: number | null;
    pending_latest_spread_abs: number | null;
    analogue_median_latest_spread_abs_same_day: number | null;
  };
};

function formatNumber(value: number | null) {
  if (value === null || value === undefined) return "N/A";
  return value.toFixed(4);
}

export default function HeadlineMetrics({ headline }: Props) {
  const cards = [
    {
      label: "Pending announcement jump",
      value: headline.pending_announcement_jump,
    },
    {
      label: "Analogue median announcement jump",
      value: headline.analogue_median_announcement_jump,
    },
    {
      label: "Pending latest spread",
      value: headline.pending_latest_spread_abs,
    },
    {
      label: "Analogue median latest spread",
      value: headline.analogue_median_latest_spread_abs_same_day,
    },
  ];

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(4, minmax(0, 1fr))",
        gap: "16px",
      }}
    >
      {cards.map((item) => (
        <div
          key={item.label}
          style={{
            background: "white",
            border: "1px solid #e2e8f0",
            borderRadius: "16px",
            padding: "16px",
          }}
        >
          <div
            style={{
              fontSize: "12px",
              color: "#64748b",
              marginBottom: "8px",
            }}
          >
            {item.label}
          </div>

          <div style={{ fontSize: "24px", fontWeight: 700 }}>
            {formatNumber(item.value)}
          </div>
        </div>
      ))}
    </div>
  );
}