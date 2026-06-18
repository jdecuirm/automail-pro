import { Mail, Send, Eye, Users } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import type { CampaignResponse } from "@/types/api";
import { mergeStats } from "@/lib/format";

interface StatsCardsProps {
  campaign: CampaignResponse;
}

interface StatCardProps {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string | number;
}

function StatCard({ icon: Icon, label, value }: StatCardProps) {
  return (
    <Card>
      <CardContent className="pt-4 pb-4">
        <div className="flex items-center gap-3">
          <div className="rounded-md bg-muted p-2 shrink-0">
            <Icon className="h-4 w-4 text-muted-foreground" />
          </div>
          <div>
            <p className="text-xs text-muted-foreground">{label}</p>
            <p className="text-xl font-bold tabular-nums">{value}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function StatsCards({ campaign }: StatsCardsProps) {
  const stats = mergeStats(campaign.stats);
  const generated =
    stats.drafted + stats.approved + stats.sent + stats.opened + stats.sending;
  const sent = stats.sent + stats.opened;
  const openRate =
    sent > 0 ? `${Math.round((stats.opened / sent) * 100)}%` : "—";

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <StatCard icon={Users} label="Total Leads" value={campaign.total_leads} />
      <StatCard icon={Mail} label="Emails Generated" value={generated} />
      <StatCard icon={Send} label="Emails Sent" value={sent} />
      <StatCard icon={Eye} label="Open Rate" value={openRate} />
    </div>
  );
}
