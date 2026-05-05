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

export default function AnalogueTable({ analogues }: Props) {
  return (
    <div
      style={{
        background: "white",
        border: "1px solid #e2e8f0",
        borderRadius: "16px",
        padding: "20px",
      }}
    >
      <h3 style={{ marginTop: 0 }}>Top analogues</h3>

      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ textAlign: "left", borderBottom: "1px solid #e2e8f0" }}>
            <th style={{ padding: "10px 8px" }}>Rank</th>
            <th style={{ padding: "10px 8px" }}>Target</th>
            <th style={{ padding: "10px 8px" }}>Tier</th>
            <th style={{ padding: "10px 8px" }}>Date</th>
            <th style={{ padding: "10px 8px" }}>Score</th>
            <th style={{ padding: "10px 8px" }}>Reasons</th>
          </tr>
        </thead>

        <tbody>
          {analogues.map((item, idx) => (
            <tr
              key={item.event_id}
              style={{ borderBottom: "1px solid #f1f5f9" }}
            >
              <td style={{ padding: "10px 8px" }}>{idx + 1}</td>
              <td style={{ padding: "10px 8px" }}>{item.target_name}</td>
              <td style={{ padding: "10px 8px" }}>{item.tier}</td>
              <td style={{ padding: "10px 8px" }}>
                {item.announcement_date ?? "N/A"}
              </td>
              <td style={{ padding: "10px 8px" }}>{item.score.toFixed(2)}</td>
              <td style={{ padding: "10px 8px" }}>
                {Array.isArray(item.reasons) ? item.reasons.join(", ") : ""}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}