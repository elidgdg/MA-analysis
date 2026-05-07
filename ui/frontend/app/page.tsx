import { AlertTriangle } from "lucide-react";
import PendingDealsList from "../components/PendingDealsList";
import DealSummary from "../components/DealSummary";
import HeadlineMetrics from "../components/HeadlineMetrics";
import AnalogueTable from "../components/AnalogueTable";
import ComparisonCharts from "../components/ComparisonCharts";
import SourcesList from "../components/SourcesList";
import InsightCommentary from "../components/InsightCommentary";
import StickyDealBar from "../components/StickyDealBar";
import { ThemeToggle } from "../components/theme-toggle";
import { Card, CardContent } from "../components/ui/card";
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
      <main className="flex min-h-screen items-center justify-center px-6">
        <Card className="max-w-md p-10 text-center">
          <h1 className="text-xl font-semibold tracking-tight">
            M&A Analogue Dashboard
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            No pending deals available. Once new deals are ingested, they will
            appear here.
          </p>
        </Card>
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

  const [summary, sourcesResponse, comparisonResult] = await Promise.all([
    fetchDealSummary(eventId),
    fetchDealSources(eventId),
    fetchDealComparison(eventId)
      .then((res) => ({ data: res.data, error: null as string | null }))
      .catch((err: any) => ({
        data: null,
        error: err?.message ?? "Comparison data is not available for this deal.",
      })),
  ]);

  const sources = sourcesResponse.sources ?? [];
  const comparison = comparisonResult.data;
  const comparisonError = comparisonResult.error;

  const analogues = comparison?.analogue_selection?.analogues ?? [];
  const headline = comparison?.headline_comparison ?? {
    pending_announcement_jump: null,
    analogue_median_announcement_jump: null,
    pending_day_5_return: null,
    analogue_median_day_5_return: null,
    pending_latest_spread_abs: null,
    analogue_median_latest_spread_abs_same_day: null,
  };

  const SENTINEL_ID = "deal-summary-end";

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-30 border-b bg-background/80 backdrop-blur-md">
        <div className="mx-auto flex w-full max-w-[1480px] items-center justify-between gap-6 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-foreground text-background">
              <span className="font-mono text-xs font-bold">M&amp;A</span>
            </div>
            <div className="flex flex-col">
              <h1 className="text-base font-semibold tracking-tight">
                Analogue Dashboard
              </h1>
              <p className="text-xs text-muted-foreground">
                Pending deal comparison & spread analytics
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden items-center gap-2 text-xs text-muted-foreground md:flex">
              <span className="font-mono tabular-nums">
                {pendingDeals.length} pending
              </span>
              <span aria-hidden>·</span>
              <span>{analogues.length} analogues</span>
              <span aria-hidden>·</span>
              <span>{sources.length} sources</span>
            </div>
            <ThemeToggle />
          </div>
        </div>
      </header>

      <StickyDealBar
        targetName={summary.target_name}
        acquirerName={summary.acquirer_name}
        pendingJump={headline.pending_announcement_jump}
        cohortJump={headline.analogue_median_announcement_jump}
        sentinelId={SENTINEL_ID}
      />

      <main className="mx-auto w-full max-w-[1480px] px-6 py-6">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[300px_minmax(0,1fr)]">
          <PendingDealsList deals={pendingDeals} selectedEventId={eventId} />

          <section className="flex animate-fade-in flex-col gap-6">
            <DealSummary summary={summary} />
            <div id={SENTINEL_ID} aria-hidden className="h-px w-full" />

            {comparisonError ? (
              <Card className="border-warning/40 bg-warning/5">
                <CardContent className="flex items-start gap-3 p-5">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-warning/15">
                    <AlertTriangle className="h-4 w-4 text-warning" aria-hidden />
                  </div>
                  <div className="flex-1">
                    <h3 className="text-sm font-semibold">
                      Comparison not available
                    </h3>
                    <p className="mt-0.5 text-sm text-muted-foreground">
                      {comparisonError}
                    </p>
                  </div>
                </CardContent>
              </Card>
            ) : (
              <>
                <HeadlineMetrics headline={headline} />

                <InsightCommentary
                  headline={headline}
                  analogueSelection={comparison.analogue_selection}
                />

                <AnalogueTable analogues={analogues} />

                <ComparisonCharts
                  pendingTargetRows={comparison.pending_target_analysis.rows}
                  pendingSpreadRows={comparison.pending_spread_analysis.rows}
                  analogueTargetReturnRows={
                    comparison.aggregated_analogue_paths
                      .target_return_from_baseline
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

            <SourcesList sources={sources} />
          </section>
        </div>
      </main>
    </div>
  );
}
