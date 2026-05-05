import PendingDealsList from "../components/PendingDealsList";
import DealSummary from "../components/DealSummary";
import HeadlineMetrics from "../components/HeadlineMetrics";
import AnalogueTable from "../components/AnalogueTable";
import ComparisonCharts from "../components/ComparisonCharts";
import SourcesList from "../components/SourcesList";
import InsightCommentary from "../components/InsightCommentary";
import {
  fetchDealComparison,
  fetchDealSources,
  fetchDealSummary,
  fetchPendingDeals,
} from "../lib/api";

type SearchParams = {
  event_id?: string;
};

export default async function HomePage({
  searchParams,
}: {
  searchParams?: SearchParams;
}) {
  const pendingDeals = await fetchPendingDeals();

  if (!pendingDeals.length) {
    return (
      <main style={{ padding: "24px" }}>
        <h1>M&A Analogue Dashboard</h1>
        <p>No pending deals available.</p>
      </main>
    );
  }

  const parsedEventId = searchParams?.event_id
    ? Number(searchParams.event_id)
    : NaN;

  const selectedEventId = Number.isFinite(parsedEventId)
    ? parsedEventId
    : pendingDeals[0].event_id;

  const selectedDeal =
    pendingDeals.find((deal: any) => deal.event_id === selectedEventId) ??
    pendingDeals[0];

  const eventId = selectedDeal.event_id;

  const summary = await fetchDealSummary(eventId);
  const sourcesResponse = await fetchDealSources(eventId);
  const sources = sourcesResponse.sources ?? [];

  let comparison: any = null;
  let comparisonError: string | null = null;

  try {
    const comparisonWrapper = await fetchDealComparison(eventId);
    comparison = comparisonWrapper.data;
  } catch (error: any) {
    comparisonError =
      error?.message ?? "Comparison data is not available for this deal.";
  }

  const analogues = comparison?.analogue_selection?.analogues ?? [];
  const headline = comparison?.headline_comparison ?? {
    pending_announcement_jump: null,
    analogue_median_announcement_jump: null,
    pending_day_5_return: null,
    analogue_median_day_5_return: null,
    pending_latest_spread_abs: null,
    analogue_median_latest_spread_abs_same_day: null,
  };

  return (
    <main style={{ padding: "24px", maxWidth: "1400px", margin: "0 auto" }}>
      <h1 style={{ fontSize: "32px", marginBottom: "8px" }}>
        M&A Analogue Dashboard
      </h1>
      <p style={{ color: "#475569", marginBottom: "24px" }}>
        Pending deal selection, analogue ranking, comparison summaries, and relevant sources.
      </p>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "280px 1fr",
          gap: "24px",
          alignItems: "start",
        }}
      >
        <PendingDealsList deals={pendingDeals} selectedEventId={eventId} />

        <section style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
          <DealSummary summary={summary} />

          <SourcesList sources={sources} />

          {comparisonError ? (
            <div
              style={{
                background: "#fff7ed",
                border: "1px solid #fdba74",
                borderRadius: "16px",
                padding: "20px",
              }}
            >
              <h3 style={{ marginTop: 0 }}>Comparison not available</h3>
              <p style={{ marginBottom: 0, color: "#9a3412" }}>
                {comparisonError}
              </p>
            </div>
          ) : (
            <>
              <InsightCommentary
                headline={headline}
                analogueSelection={comparison.analogue_selection}
              />

              <HeadlineMetrics headline={headline} />

              <AnalogueTable analogues={analogues} />

              <ComparisonCharts
                pendingTargetRows={comparison.pending_target_analysis.rows}
                pendingSpreadRows={comparison.pending_spread_analysis.rows}
                analogueTargetReturnRows={
                  comparison.aggregated_analogue_paths.target_return_from_baseline
                }
                analogueSpreadRows={
                  comparison.aggregated_analogue_paths.spread_abs
                }
                analogueVolumeRows={
                  comparison.aggregated_analogue_paths.target_volume_ratio
                }
              />
            </>
          )}
        </section>
      </div>
    </main>
  );
}