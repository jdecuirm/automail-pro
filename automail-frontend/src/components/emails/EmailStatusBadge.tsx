import { Badge } from "@/components/ui/badge";
import type { EmailStatus } from "@/types/api";

const STATUS_CONFIG: Record<EmailStatus, { label: string; className: string }> =
  {
    draft: {
      label: "Draft",
      className: "bg-muted text-muted-foreground hover:bg-muted",
    },
    approved: {
      label: "Approved",
      className:
        "bg-blue-100 text-blue-700 hover:bg-blue-100 dark:bg-blue-900/30 dark:text-blue-400",
    },
    rejected: {
      label: "Rejected",
      className: "bg-destructive/10 text-destructive hover:bg-destructive/10",
    },
    sending: {
      label: "Sending",
      className:
        "bg-amber-100 text-amber-700 hover:bg-amber-100 dark:bg-amber-900/30 dark:text-amber-400",
    },
    sent: {
      label: "Sent",
      className:
        "bg-green-100 text-green-700 hover:bg-green-100 dark:bg-green-900/30 dark:text-green-400",
    },
    failed: {
      label: "Failed",
      className:
        "bg-destructive/15 text-destructive hover:bg-destructive/15 font-medium",
    },
  };

export default function EmailStatusBadge({ status }: { status: EmailStatus }) {
  const { label, className } = STATUS_CONFIG[status];
  return (
    <Badge variant="secondary" className={className}>
      {label}
    </Badge>
  );
}
