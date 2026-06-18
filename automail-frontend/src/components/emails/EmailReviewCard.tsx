import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import EmailStatusBadge from "./EmailStatusBadge";
import EmailEditor from "./EmailEditor";
import { useApproveEmail, useRejectEmail } from "@/hooks/useEmailMutations";
import type { EmailResponse } from "@/types/api";

function initials(name: string): string {
  return name
    .split(" ")
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase();
}

interface EmailReviewCardProps {
  email: EmailResponse;
  campaignId: string;
}

export default function EmailReviewCard({
  email,
  campaignId,
}: EmailReviewCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [editing, setEditing] = useState(false);
  const approveMutation = useApproveEmail(campaignId);
  const rejectMutation = useRejectEmail(campaignId);

  const isDraft = email.status === "draft";
  const previewLines = email.body_text.split("\n").slice(0, 4).join("\n");

  return (
    <>
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-3 min-w-0">
              <Avatar className="h-8 w-8 shrink-0">
                <AvatarFallback className="text-xs">
                  {initials(email.lead_name)}
                </AvatarFallback>
              </Avatar>
              <div className="min-w-0">
                <p className="text-sm font-medium truncate">
                  {email.lead_name}
                </p>
                <p className="text-xs text-muted-foreground truncate">
                  {email.lead_email}
                  {email.lead_company ? ` · ${email.lead_company}` : ""}
                </p>
              </div>
            </div>
            <EmailStatusBadge status={email.status} />
          </div>
        </CardHeader>

        <CardContent className="space-y-2 pb-3">
          <p className="text-sm font-semibold">{email.subject}</p>
          <p className="text-xs text-muted-foreground whitespace-pre-line line-clamp-4">
            {previewLines}
          </p>
          {email.body_text.split("\n").length > 4 && (
            <Button
              variant="ghost"
              size="sm"
              className="h-6 px-2 text-xs -ml-2"
              onClick={() => setExpanded((v) => !v)}
            >
              {expanded ? (
                <>
                  <ChevronUp className="h-3 w-3 mr-1" /> Hide
                </>
              ) : (
                <>
                  <ChevronDown className="h-3 w-3 mr-1" /> Show full preview
                </>
              )}
            </Button>
          )}
          {expanded && (
            <p className="text-xs text-muted-foreground whitespace-pre-line">
              {email.body_text}
            </p>
          )}

          {email.status === "sent" && email.sent_at && (
            <p className="text-xs text-muted-foreground">
              Sent {new Date(email.sent_at).toLocaleString()}
              {email.gmail_message_id && (
                <span className="ml-1 text-muted-foreground/60">
                  · {email.gmail_message_id.slice(0, 16)}…
                </span>
              )}
            </p>
          )}

          {email.status === "failed" && email.error_message && (
            <Alert variant="destructive" className="py-2">
              <AlertDescription className="text-xs">
                {email.error_message}
              </AlertDescription>
            </Alert>
          )}
        </CardContent>

        {isDraft && (
          <>
            <Separator />
            <CardFooter className="pt-3 gap-2 flex-wrap">
              <Button
                variant="outline"
                size="sm"
                className="text-destructive border-destructive/30 hover:bg-destructive/5 hover:text-destructive"
                onClick={() => rejectMutation.mutate(email.id)}
                disabled={rejectMutation.isPending || approveMutation.isPending}
              >
                Reject
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setEditing(true)}
                disabled={rejectMutation.isPending || approveMutation.isPending}
              >
                Edit
              </Button>
              <Button
                size="sm"
                onClick={() => approveMutation.mutate(email.id)}
                disabled={approveMutation.isPending || rejectMutation.isPending}
                className="ml-auto"
              >
                {approveMutation.isPending ? "Approving…" : "Approve"}
              </Button>
            </CardFooter>
          </>
        )}
      </Card>

      <EmailEditor
        email={editing ? email : null}
        campaignId={campaignId}
        onClose={() => setEditing(false)}
      />
    </>
  );
}
