import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Eye } from "lucide-react";
import EmptyState from "@/components/common/EmptyState";
import type { CampaignStats } from "@/types/api";

interface OpenRateChartProps {
  stats: CampaignStats;
}

export default function OpenRateChart({ stats }: OpenRateChartProps) {
  const sent = stats.sent + stats.opened;
  const opened = stats.opened;

  if (sent === 0) {
    return (
      <EmptyState
        icon={Eye}
        title="No opens yet"
        description="Opens will appear here once emails are sent and opened"
      />
    );
  }

  const data = [
    { name: "Sent", value: sent },
    { name: "Opened", value: opened },
  ];

  return (
    <div className="h-[260px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={data}
          margin={{ top: 8, right: 16, left: 0, bottom: 8 }}
        >
          <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
          <XAxis
            dataKey="name"
            tick={{ fontSize: 12 }}
            className="fill-muted-foreground"
          />
          <YAxis
            allowDecimals={false}
            tick={{ fontSize: 12 }}
            className="fill-muted-foreground"
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "hsl(var(--popover))",
              border: "1px solid hsl(var(--border))",
              borderRadius: "6px",
              fontSize: "12px",
            }}
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke="hsl(var(--primary))"
            strokeWidth={2}
            dot={{ r: 4, fill: "hsl(var(--primary))" }}
            activeDot={{ r: 6 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
