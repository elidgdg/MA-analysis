type SourceItem = {
  rank: number;
  title: string;
  url: string;
  publisher: string | null;
  published_at: string | null;
  source_type: string | null;
};

type Props = {
  sources: SourceItem[];
};

export default function SourcesList({ sources }: Props) {
  return (
    <div
      style={{
        background: "white",
        border: "1px solid #e2e8f0",
        borderRadius: "16px",
        padding: "20px",
      }}
    >
      <h3 style={{ marginTop: 0 }}>Sources / News</h3>

      {sources.length === 0 ? (
        <p style={{ color: "#64748b", marginBottom: 0 }}>
          No sources available yet for this deal.
        </p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
          {sources.map((source) => (
            <a
              key={`${source.rank}-${source.url}`}
              href={source.url}
              target="_blank"
              rel="noreferrer"
              style={{
                display: "block",
                border: "1px solid #e2e8f0",
                borderRadius: "12px",
                padding: "14px",
                background: "#ffffff",
              }}
            >
              <div style={{ fontWeight: 600, marginBottom: "6px" }}>
                {source.title}
              </div>

              <div style={{ fontSize: "13px", color: "#64748b" }}>
                {source.publisher ?? "Unknown publisher"}
                {source.published_at ? ` · ${source.published_at.slice(0, 10)}` : ""}
                {source.source_type ? ` · ${source.source_type}` : ""}
              </div>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}