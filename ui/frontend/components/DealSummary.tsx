type Props = {
  summary: {
    target_name: string;
    acquirer_name: string | null;
    payment_type: string | null;
    target_sector: string | null;
    announcement_date: string | null;
    expected_completion_date: string | null;
    announced_total_value_mil: number | null;
    nature_of_bid: string | null;
    percent_owned_sought: number | null;
  };
};

export default function DealSummary({ summary }: Props) {
  return (
    <div
      style={{
        background: "white",
        border: "1px solid #e2e8f0",
        borderRadius: "16px",
        padding: "20px",
      }}
    >
      <h2 style={{ marginTop: 0, marginBottom: "8px" }}>
        {summary.target_name} / {summary.acquirer_name ?? "Unknown acquirer"}
      </h2>

      <div style={{ color: "#475569" }}>
        {summary.payment_type ?? "N/A"} · {summary.target_sector ?? "N/A"} ·
        Announcement: {summary.announcement_date ?? "N/A"}
      </div>

      <div style={{ color: "#475569", marginTop: "6px" }}>
        Expected completion: {summary.expected_completion_date ?? "N/A"}
      </div>

      <div style={{ color: "#475569", marginTop: "6px" }}>
        Announced deal value (mil):{" "}
        {summary.announced_total_value_mil ?? "N/A"}
      </div>

      <div style={{ color: "#475569", marginTop: "6px" }}>
        Nature of bid: {summary.nature_of_bid ?? "N/A"}
      </div>

      <div style={{ color: "#475569", marginTop: "6px" }}>
        Percent sought: {summary.percent_owned_sought ?? "N/A"}
      </div>
    </div>
  );
}