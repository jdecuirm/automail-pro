import type { CampaignResponse } from "@/types/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

interface CampaignProgressProps {
  campaign: CampaignResponse;
}

function StatCard({
  label,
  value,
  variant,
}: {
  label: string;
  value: number;
  variant?: "default" | "success" | "destructive";
}) {
  const colorClass =
    variant === "success"
      ? "text-green-600 dark:text-green-400"
      : variant === "destructive"
        ? "text-destructive"
        : "text-foreground";
  return (
    <div className="text-center">
      <p className={`text-2xl font-bold tabular-nums ${colorClass}`}>{value}</p>
      <p className="text-xs text-muted-foreground mt-0.5">{label}</p>
    </div>
  );
}

export default function CampaignProgress({ campaign }: CampaignProgressProps) {
  const { stats, total_leads } = campaign;
  const processed =
    stats.drafted + stats.approved + stats.sent + stats.opened + stats.failed;
  const progressPct =
    total_leads > 0 ? Math.round((processed / total_leads) * 100) : 0;

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium">
          Processing Progress
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Progress bar */}
        <div className="space-y-1.5">
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>
              {processed} / {total_leads} leads processed
            </span>
            <span>{progressPct}%</span>
          </div>
          <Progress value={progressPct} className="h-2" />
        </div>

        {/* Stat cards */}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatCard label="Uploaded" value={stats.uploaded + stats.scraping} />
          <StatCard
            label="Researched"
            value={stats.researched + stats.generating}
          />
          <StatCard label="Drafted" value={stats.drafted + stats.approved} />
          <StatCard
            label="Sent"
            value={stats.sent + stats.opened}
            variant="success"
          />
        </div>

        {stats.failed > 0 && (
          <div className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive">
            {stats.failed} lead{stats.failed === 1 ? "" : "s"} failed to
            process.
          </div>
        )}
      </CardContent>
    </Card>
  );
}
