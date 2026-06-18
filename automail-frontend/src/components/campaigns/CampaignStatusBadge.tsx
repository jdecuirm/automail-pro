import type { CampaignStatus } from "@/types/api";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const STATUS_CONFIG: Record<
  CampaignStatus,
  { label: string; className: string }
> = {
  draft: {
    label: "Draft",
    className: "bg-muted text-muted-foreground border-muted-foreground/20",
  },
  uploaded: {
    label: "Uploaded",
    className:
      "bg-yellow-50 text-yellow-700 border-yellow-300 dark:bg-yellow-900/20 dark:text-yellow-400 dark:border-yellow-700",
  },
  scraping: {
    label: "Scraping",
    className:
      "bg-yellow-50 text-yellow-700 border-yellow-300 dark:bg-yellow-900/20 dark:text-yellow-400 dark:border-yellow-700",
  },
  generating: {
    label: "Generating",
    className:
      "bg-yellow-50 text-yellow-700 border-yellow-300 dark:bg-yellow-900/20 dark:text-yellow-400 dark:border-yellow-700",
  },
  review: {
    label: "Review",
    className:
      "bg-blue-50 text-blue-700 border-blue-300 dark:bg-blue-900/20 dark:text-blue-400 dark:border-blue-700",
  },
  sending: {
    label: "Sending",
    className:
      "bg-amber-50 text-amber-700 border-amber-300 dark:bg-amber-900/20 dark:text-amber-400 dark:border-amber-700",
  },
  completed: {
    label: "Completed",
    className:
      "bg-green-50 text-green-700 border-green-300 dark:bg-green-900/20 dark:text-green-400 dark:border-green-700",
  },
  paused: {
    label: "Paused",
    className: "bg-muted text-muted-foreground border-muted-foreground/20",
  },
  failed: {
    label: "Failed",
    className:
      "bg-red-50 text-red-700 border-red-300 dark:bg-red-900/20 dark:text-red-400 dark:border-red-700",
  },
};

export default function CampaignStatusBadge({
  status,
}: {
  status: CampaignStatus;
}) {
  const config = STATUS_CONFIG[status];
  return (
    <Badge
      variant="outline"
      className={cn("text-xs font-medium", config.className)}
    >
      {config.label}
    </Badge>
  );
}
