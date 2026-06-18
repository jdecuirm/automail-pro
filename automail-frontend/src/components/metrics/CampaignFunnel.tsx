import type { CampaignResponse } from "@/types/api";
import { mergeStats } from "@/lib/format";

interface FunnelStep {
  label: string;
  value: number;
  colorClass: string;
}

interface CampaignFunnelProps {
  campaign: CampaignResponse;
}

export default function CampaignFunnel({ campaign }: CampaignFunnelProps) {
  const stats = mergeStats(campaign.stats);
  const total = campaign.total_leads;

  const steps: FunnelStep[] = [
    {
      label: "Uploaded",
      value: total,
      colorClass: "bg-muted-foreground/20",
    },
    {
      label: "Researched",
      value:
        stats.researched +
        stats.generating +
        stats.drafted +
        stats.approved +
        stats.rejected +
        stats.sending +
        stats.sent +
        stats.opened +
        stats.failed,
      colorClass: "bg-blue-200 dark:bg-blue-900/50",
    },
    {
      label: "Drafted",
      value:
        stats.drafted +
        stats.approved +
        stats.rejected +
        stats.sending +
        stats.sent +
        stats.opened,
      colorClass: "bg-violet-200 dark:bg-violet-900/50",
    },
    {
      label: "Sent",
      value: stats.sent + stats.opened,
      colorClass: "bg-green-200 dark:bg-green-900/50",
    },
    {
      label: "Opened",
      value: stats.opened,
      colorClass: "bg-emerald-300 dark:bg-emerald-800/60",
    },
  ];

  return (
    <div className="space-y-2">
      {steps.map((step) => {
        const pct = total > 0 ? Math.round((step.value / total) * 100) : 0;
        return (
          <div key={step.label} className="space-y-0.5">
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>{step.label}</span>
              <span className="tabular-nums">
                {step.value} <span className="opacity-60">({pct}%)</span>
              </span>
            </div>
            <div className="h-6 w-full rounded bg-muted overflow-hidden">
              <div
                className={`h-full rounded transition-all duration-500 ${step.colorClass}`}
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
