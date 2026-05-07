"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { formatEventDay, formatNumber, formatPct, formatRatio } from "../lib/format";

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

type ValueFormatter = (value: unknown) => string;

const SERIES = {
  pending: "hsl(var(--chart-pending))",
  median: "hsl(var(--chart-median))",
  mean: "hsl(var(--chart-mean))",
};

const fmtPctValue: ValueFormatter = (value) =>
  typeof value === "number" ? formatPct(value, { signed: true }) : "—";

const fmtNumValue: ValueFormatter = (value) =>
  typeof value === "number" ? formatNumber(value, { digits: 4 }) : "—";

const fmtRatioValue: ValueFormatter = (value) =>
  typeof value === "number" ? formatRatio(value) : "—";

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

function CustomTooltip({
  active,
  payload,
  label,
  formatter,
}: {
  active?: boolean;
  payload?: any[];
  label?: number | string;
  formatter: ValueFormatter;
}) {
  if (!active || !payload || payload.length === 0) return null;
  const day = typeof label === "number" ? formatEventDay(label) : String(label ?? "");
  return (
    <div className="rounded-lg border bg-popover p-3 text-xs shadow-lg">
      <div className="mb-1.5 font-mono font-medium text-popover-foreground">
        Event day {day}
      </div>
      <div className="flex flex-col gap-1">
        {payload.map((entry: any) => (
          <div key={entry.dataKey} className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <span
                className="h-2 w-2 rounded-full"
                style={{ background: entry.color }}
                aria-hidden
              />
              <span className="text-muted-foreground">{entry.name}</span>
            </div>
            <span className="font-mono tabular-nums text-popover-foreground">
              {formatter(entry.value)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function ChartCard({
  title,
  description,
  data,
  syncId,
  valueFormatter,
  yTickFormatter,
}: {
  title: string;
  description: string;
  data: ChartRow[];
  syncId: string;
  valueFormatter: ValueFormatter;
  yTickFormatter: (value: number) => string;
}) {
  return (
    <Card className="transition-shadow hover:shadow-md">
      <CardHeader className="space-y-1">
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>

      <CardContent>
        <div className="h-[300px] w-full">
          <ResponsiveContainer>
            <LineChart
              data={data}
              syncId={syncId}
              margin={{ top: 8, right: 12, left: -8, bottom: 4 }}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="hsl(var(--border))"
                vertical={false}
              />
              <XAxis
                dataKey="event_day"
                tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }}
                tickLine={false}
                axisLine={{ stroke: "hsl(var(--border))" }}
                tickFormatter={(value) =>
                  typeof value === "number" ? formatEventDay(value) : String(value)
                }
              />
              <YAxis
                tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                width={56}
                tickFormatter={(value) =>
                  typeof value === "number" ? yTickFormatter(value) : String(value)
                }
              />
              <ReferenceLine
                x={0}
                stroke="hsl(var(--accent))"
                strokeDasharray="4 4"
                strokeOpacity={0.5}
                label={{
                  value: "announce",
                  position: "insideTopRight",
                  fontSize: 10,
                  fill: "hsl(var(--accent))",
                }}
              />
              <Tooltip
                content={(props: any) => (
                  <CustomTooltip {...props} formatter={valueFormatter} />
                )}
                cursor={{ stroke: "hsl(var(--border))" }}
              />
              <Legend
                iconType="circle"
                iconSize={8}
                wrapperStyle={{ fontSize: "12px", paddingTop: "8px" }}
              />
              <Line
                type="monotone"
                dataKey="pending"
                name="Pending"
                stroke={SERIES.pending}
                strokeWidth={2.5}
                dot={false}
                connectNulls
                activeDot={{ r: 4 }}
              />
              <Line
                type="monotone"
                dataKey="analogueMedian"
                name="Analogue median"
                stroke={SERIES.median}
                strokeWidth={1.75}
                dot={false}
                connectNulls
              />
              <Line
                type="monotone"
                dataKey="analogueMean"
                name="Analogue mean"
                stroke={SERIES.mean}
                strokeWidth={1.75}
                strokeDasharray="4 3"
                dot={false}
                connectNulls
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
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

  const mergedReturn = buildMergedSeries(pendingReturnSeries, analogueTargetReturnRows);
  const mergedSpread = buildMergedSeries(pendingSpreadSeries, analogueSpreadRows);
  const mergedVolume = buildMergedSeries(pendingVolumeSeries, analogueVolumeRows);

  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
      <ChartCard
        title="Target return path"
        description="Cumulative return from baseline"
        data={mergedReturn}
        syncId="comparison"
        valueFormatter={fmtPctValue}
        yTickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
      />
      <ChartCard
        title="Spread path"
        description="Absolute spread vs offer price"
        data={mergedSpread}
        syncId="comparison"
        valueFormatter={fmtNumValue}
        yTickFormatter={(v) => v.toFixed(2)}
      />
      <div className="xl:col-span-2">
        <ChartCard
          title="Volume ratio path"
          description="Trading volume relative to baseline"
          data={mergedVolume}
          syncId="comparison"
          valueFormatter={fmtRatioValue}
          yTickFormatter={(v) => `${v.toFixed(1)}×`}
        />
      </div>
    </div>
  );
}
