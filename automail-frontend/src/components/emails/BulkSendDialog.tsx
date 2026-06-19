import { AlertCircle } from "lucide-react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { useBulkSend } from "@/hooks/useEmailMutations";
import type { EmailResponse } from "@/types/api";

const MAX_DAILY = 50;

interface BulkSendDialogProps {
  open: boolean;
  onClose: () => void;
  campaignId: string;
  emails: EmailResponse[];
  profileComplete: boolean;
}

export default function BulkSendDialog({
  open,
  onClose,
  campaignId,
  emails,
  profileComplete,
}: BulkSendDialogProps) {
  const bulkSend = useBulkSend(campaignId);
  const approvedCount = emails.filter((e) => e.status === "approved").length;
  const willExceed = approvedCount > MAX_DAILY;

  function handleSend() {
    bulkSend.mutate(undefined, { onSuccess: onClose, onError: onClose });
  }

  return (
    <AlertDialog
      open={open}
      onOpenChange={(o) => {
        if (!o) onClose();
      }}
    >
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Send approved emails</AlertDialogTitle>
          <AlertDialogDescription asChild>
            <div className="space-y-2 text-sm">
              {!profileComplete && (
                <div className="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-destructive">
                  <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
                  <span>
                    Your sender profile is incomplete. Go to{" "}
                    <strong>Settings → Account</strong> to set your name and
                    company before sending.
                  </span>
                </div>
              )}
              <p>
                You are about to send{" "}
                <span className="font-semibold">{approvedCount}</span> approved
                email{approvedCount === 1 ? "" : "s"}.
              </p>
              <p className="text-muted-foreground">
                Daily limit: {MAX_DAILY} emails per Gmail account.
              </p>
              {willExceed && (
                <div className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-amber-800 dark:border-amber-700 dark:bg-amber-900/20 dark:text-amber-300">
                  Only {MAX_DAILY} emails will be sent today. The remaining{" "}
                  {approvedCount - MAX_DAILY} will stay approved and can be sent
                  tomorrow.
                </div>
              )}
            </div>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction
            onClick={handleSend}
            disabled={
              bulkSend.isPending || approvedCount === 0 || !profileComplete
            }
          >
            {bulkSend.isPending
              ? "Sending…"
              : `Send ${approvedCount} email${approvedCount === 1 ? "" : "s"}`}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
