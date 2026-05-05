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

export default function PendingDealsList({ deals, selectedEventId }: Props) {
  return (
    <aside
      style={{
        background: "white",
        border: "1px solid #e2e8f0",
        borderRadius: "16px",
        padding: "16px",
      }}
    >
      <h2 style={{ fontSize: "18px", marginTop: 0 }}>Pending deals</h2>

      <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
        {deals.map((deal) => {
          const selected = deal.event_id === selectedEventId;

          return (
            <a
              key={deal.event_id}
              href={`/?event_id=${deal.event_id}`}
              style={{
                border: "1px solid #cbd5e1",
                borderRadius: "12px",
                padding: "12px",
                background: selected ? "#f1f5f9" : "white",
                display: "block",
              }}
            >
              <div style={{ fontWeight: 600 }}>{deal.target_name}</div>

              <div
                style={{
                  fontSize: "14px",
                  color: "#475569",
                  marginTop: "4px",
                }}
              >
                {deal.acquirer_name ?? "Unknown acquirer"}
              </div>

              <div
                style={{
                  fontSize: "13px",
                  color: "#64748b",
                  marginTop: "6px",
                }}
              >
                {deal.payment_type ?? "N/A"} · {deal.target_sector ?? "N/A"}
              </div>

              <div
                style={{
                  fontSize: "12px",
                  color: "#94a3b8",
                  marginTop: "6px",
                }}
              >
                {deal.announcement_date ?? "No announcement date"}
              </div>
            </a>
          );
        })}
      </div>
    </aside>
  );
}