"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

type PendingTargetRow = {
  event_day: number;
  return_from_baseline?: number | null;
  volume_ratio?: number | null;
};

type PendingSpreadRow = {
  event_day: number;
  spread_abs?: number | null;
};

type AggregateRow = {
  event_day: number;
  median: number | null;
  mean: number | null;
};

type Props = {
  pendingTargetRows: PendingTargetRow[];
  pendingSpreadRows: PendingSpreadRow[];
  analogueTargetReturnRows: AggregateRow[];
  analogueSpreadRows: AggregateRow[];
  analogueVolumeRows: AggregateRow[];
};

type ChartRow = {
  event_day: number;
  pending?: number | null;
  analogueMedian?: number | null;
  analogueMean?: number | null;
};

function buildMergedSeries(
  pendingRows: Array<{ event_day: number; value: number | null }>,
  aggregateRows: AggregateRow[]
): ChartRow[] {
  const byDay = new Map<number, ChartRow>();

  for (const row of pendingRows) {
    const current = byDay.get(row.event_day) ?? { event_day: row.event_day };
    current.pending = row.value;
    byDay.set(row.event_day, current);
  }

  for (const row of aggregateRows) {
    const current = byDay.get(row.event_day) ?? { event_day: row.event_day };
    current.analogueMedian = row.median;
    current.analogueMean = row.mean;
    byDay.set(row.event_day, current);
  }

  return Array.from(byDay.values()).sort((a, b) => a.event_day - b.event_day);
}

function formatNumber(value: unknown) {
  if (typeof value !== "number" || Number.isNaN(value)) return "N/A";
  return value.toFixed(4);
}

function ChartCard({
  title,
  data,
  yLabel,
}: {
  title: string;
  data: ChartRow[];
  yLabel: string;
}) {
  return (
    <div
      style={{
        background: "white",
        border: "1px solid #e2e8f0",
        borderRadius: "16px",
        padding: "20px",
      }}
    >
      <h3 style={{ marginTop: 0, marginBottom: "16px" }}>{title}</h3>

      <div style={{ width: "100%", height: 320 }}>
        <ResponsiveContainer>
          <LineChart
            data={data}
            margin={{ top: 10, right: 20, left: 10, bottom: 10 }}
          >
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="event_day" label={{ value: "Event day", position: "insideBottom", offset: -5 }} />
            <YAxis
              label={{
                value: yLabel,
                angle: -90,
                position: "insideLeft",
              }}
            />
            <Tooltip
              formatter={(value) => formatNumber(value)}
            />
            <Legend />
            <Line
              type="monotone"
              dataKey="pending"
              name="Pending deal"
              stroke="#0f172a"
              strokeWidth={3}
              dot={false}
              connectNulls
            />
            <Line
              type="monotone"
              dataKey="analogueMedian"
              name="Analogue median"
              stroke="#2563eb"
              strokeWidth={2}
              dot={false}
              connectNulls
            />
            <Line
              type="monotone"
              dataKey="analogueMean"
              name="Analogue mean"
              stroke="#f97316"
              strokeWidth={2}
              dot={false}
              connectNulls
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export default function ComparisonCharts({
  pendingTargetRows,
  pendingSpreadRows,
  analogueTargetReturnRows,
  analogueSpreadRows,
  analogueVolumeRows,
}: Props) {
  const pendingReturnSeries = pendingTargetRows.map((row) => ({
    event_day: row.event_day,
    value: row.return_from_baseline ?? null,
  }));

  const pendingVolumeSeries = pendingTargetRows.map((row) => ({
    event_day: row.event_day,
    value: row.volume_ratio ?? null,
  }));

  const pendingSpreadSeries = pendingSpreadRows.map((row) => ({
    event_day: row.event_day,
    value: row.spread_abs ?? null,
  }));

  const mergedReturn = buildMergedSeries(
    pendingReturnSeries,
    analogueTargetReturnRows
  );

  const mergedSpread = buildMergedSeries(
    pendingSpreadSeries,
    analogueSpreadRows
  );

  const mergedVolume = buildMergedSeries(
    pendingVolumeSeries,
    analogueVolumeRows
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      <ChartCard
        title="Target return path"
        data={mergedReturn}
        yLabel="Return"
      />

      <ChartCard
        title="Spread path"
        data={mergedSpread}
        yLabel="Spread"
      />

      <ChartCard
        title="Volume ratio path"
        data={mergedVolume}
        yLabel="Volume ratio"
      />
    </div>
  );
}