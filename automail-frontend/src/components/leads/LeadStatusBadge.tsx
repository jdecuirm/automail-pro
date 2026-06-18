import type { LeadStatus } from "@/types/api";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const STATUS_CONFIG: Record<LeadStatus, { label: string; className: string }> =
  {
    uploaded: {
      label: "Uploaded",
      className:
        "bg-slate-50 text-slate-600 border-slate-300 dark:bg-slate-900/20 dark:text-slate-400 dark:border-slate-700",
    },
    scraping: {
      label: "Scraping",
      className:
        "bg-yellow-50 text-yellow-700 border-yellow-300 dark:bg-yellow-900/20 dark:text-yellow-400 dark:border-yellow-700",
    },
    researched: {
      label: "Researched",
      className:
        "bg-purple-50 text-purple-700 border-purple-300 dark:bg-purple-900/20 dark:text-purple-400 dark:border-purple-700",
    },
    generating: {
      label: "Generating",
      className:
        "bg-purple-50 text-purple-700 border-purple-300 dark:bg-purple-900/20 dark:text-purple-400 dark:border-purple-700",
    },
    drafted: {
      label: "Drafted",
      className:
        "bg-blue-50 text-blue-700 border-blue-300 dark:bg-blue-900/20 dark:text-blue-400 dark:border-blue-700",
    },
    approved: {
      label: "Approved",
      className:
        "bg-green-50 text-green-700 border-green-300 dark:bg-green-900/20 dark:text-green-400 dark:border-green-700",
    },
    rejected: {
      label: "Rejected",
      className: "bg-muted text-muted-foreground border-muted-foreground/20",
    },
    sending: {
      label: "Sending",
      className:
        "bg-amber-50 text-amber-700 border-amber-300 dark:bg-amber-900/20 dark:text-amber-400 dark:border-amber-700",
    },
    sent: {
      label: "Sent",
      className:
        "bg-green-50 text-green-700 border-green-300 dark:bg-green-900/20 dark:text-green-400 dark:border-green-700",
    },
    opened: {
      label: "Opened",
      className:
        "bg-emerald-50 text-emerald-700 border-emerald-300 dark:bg-emerald-900/20 dark:text-emerald-400 dark:border-emerald-700",
    },
    failed: {
      label: "Failed",
      className:
        "bg-red-50 text-red-700 border-red-300 dark:bg-red-900/20 dark:text-red-400 dark:border-red-700",
    },
  };

export default function LeadStatusBadge({ status }: { status: LeadStatus }) {
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
