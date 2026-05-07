import { Badge } from "./ui/badge";
import { Card, CardContent } from "./ui/card";
import { formatDate, formatUSDMil } from "../lib/format";

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

function formatPercent(value: number | null) {
  if (value === null || value === undefined) return "—";
  return `${value.toFixed(1)}%`;
}

function MetaCell({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
        {label}
      </span>
      <span className="text-sm font-medium text-foreground">{value ?? "—"}</span>
    </div>
  );
}

export default function DealSummary({ summary }: Props) {
  return (
    <Card className="overflow-hidden">
      <div className="bg-grid border-b bg-muted/30 px-6 py-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex flex-col gap-1">
            <span className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
              Pending deal
            </span>
            <h2 className="text-2xl font-semibold tracking-tight">
              {summary.target_name}{" "}
              <span className="text-muted-foreground">←</span>{" "}
              <span className="font-medium text-foreground/80">
                {summary.acquirer_name ?? "Unknown acquirer"}
              </span>
            </h2>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {summary.payment_type && (
              <Badge variant="secondary">{summary.payment_type}</Badge>
            )}
            {summary.nature_of_bid && (
              <Badge variant="outline">{summary.nature_of_bid}</Badge>
            )}
            {summary.target_sector && (
              <Badge variant="muted">{summary.target_sector}</Badge>
            )}
          </div>
        </div>
      </div>

      <CardContent className="grid grid-cols-2 gap-x-6 gap-y-5 p-6 sm:grid-cols-3 lg:grid-cols-5">
        <MetaCell label="Announced" value={formatDate(summary.announcement_date)} />
        <MetaCell label="Expected close" value={formatDate(summary.expected_completion_date)} />
        <MetaCell label="Deal value" value={formatUSDMil(summary.announced_total_value_mil)} />
        <MetaCell label="% sought" value={formatPercent(summary.percent_owned_sought)} />
        <MetaCell label="Sector" value={summary.target_sector} />
      </CardContent>
    </Card>
  );
}
