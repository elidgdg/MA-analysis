type PathRow = {
  event_day: number;
  count: number;
  median: number | null;
  mean: number | null;
};

type Props = {
  title: string;
  rows: PathRow[];
};

function fmt(value: number | null) {
  if (value === null || value === undefined) return "N/A";
  return value.toFixed(4);
}

export default function ComparisonPathTable({ title, rows }: Props) {
  return (
    <div
      style={{
        background: "white",
        border: "1px solid #e2e8f0",
        borderRadius: "16px",
        padding: "20px",
      }}
    >
      <h3 style={{ marginTop: 0 }}>{title}</h3>

      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ textAlign: "left", borderBottom: "1px solid #e2e8f0" }}>
            <th style={{ padding: "10px 8px" }}>Event day</th>
            <th style={{ padding: "10px 8px" }}>Count</th>
            <th style={{ padding: "10px 8px" }}>Median</th>
            <th style={{ padding: "10px 8px" }}>Mean</th>
          </tr>
        </thead>

        <tbody>
          {rows.map((row) => (
            <tr key={row.event_day} style={{ borderBottom: "1px solid #f1f5f9" }}>
              <td style={{ padding: "10px 8px" }}>{row.event_day}</td>
              <td style={{ padding: "10px 8px" }}>{row.count}</td>
              <td style={{ padding: "10px 8px" }}>{fmt(row.median)}</td>
              <td style={{ padding: "10px 8px" }}>{fmt(row.mean)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}