import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import LeadStatusBadge from "./LeadStatusBadge";
import type { LeadResponse } from "@/types/api";

interface LeadDetailDialogProps {
  lead: LeadResponse | null;
  onClose: () => void;
}

function InfoRow({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="flex justify-between gap-4 text-sm">
      <span className="text-muted-foreground shrink-0">{label}</span>
      <span className="text-right break-all min-w-0">
        {value ?? <span className="text-muted-foreground">—</span>}
      </span>
    </div>
  );
}

export default function LeadDetailDialog({
  lead,
  onClose,
}: LeadDetailDialogProps) {
  return (
    <Dialog
      open={lead !== null}
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <DialogContent className="max-w-md">
        {lead && (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2 flex-wrap">
                {lead.name}
                <LeadStatusBadge status={lead.status} />
              </DialogTitle>
            </DialogHeader>

            <div className="space-y-3">
              <InfoRow label="Email" value={lead.email} />
              <Separator />
              <InfoRow label="Company" value={lead.company} />
              <Separator />
              <InfoRow label="Website" value={lead.website} />
              <Separator />
              <InfoRow label="LinkedIn" value={lead.linkedin_url} />

              {lead.error_message && (
                <>
                  <Separator />
                  <div className="rounded-md bg-destructive/5 border border-destructive/30 px-3 py-2">
                    <p className="text-xs font-medium text-destructive mb-1">
                      Error
                    </p>
                    <p className="text-xs text-destructive/80">
                      {lead.error_message}
                    </p>
                  </div>
                </>
              )}

              <Separator />
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>Status</span>
                <Badge variant="outline" className="text-xs">
                  {lead.status}
                </Badge>
              </div>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
