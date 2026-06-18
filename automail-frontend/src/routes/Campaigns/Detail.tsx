import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ArrowLeft, Trash2, Mail, Send, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import CampaignStatusBadge from "@/components/campaigns/CampaignStatusBadge";
import CampaignProgress from "@/components/campaigns/CampaignProgress";
import LeadsTable from "@/components/leads/LeadsTable";
import EmailReviewCard from "@/components/emails/EmailReviewCard";
import BulkSendDialog from "@/components/emails/BulkSendDialog";
import EmptyState from "@/components/common/EmptyState";
import StatsCards from "@/components/metrics/StatsCards";
import CampaignFunnel from "@/components/metrics/CampaignFunnel";
import OpenRateChart from "@/components/metrics/OpenRateChart";
import { useCampaign } from "@/hooks/useCampaign";
import { useCampaignEmails } from "@/hooks/useCampaignEmails";
import { deleteCampaign } from "@/api/campaigns";
import { fullDateTime } from "@/lib/format";

export default function CampaignDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data: campaign, isPending, isError } = useCampaign(id ?? "");

  // Must be called unconditionally (Rules of Hooks) — before any early returns
  const [emailSearch, setEmailSearch] = useState("");
  const [bulkSendOpen, setBulkSendOpen] = useState(false);
  const { data: emails = [], isPending: emailsPending } = useCampaignEmails(
    id ?? "",
    campaign?.status,
  );

  const filteredEmails = emails.filter((e) => {
    const q = emailSearch.toLowerCase();
    return (
      e.lead_name.toLowerCase().includes(q) ||
      e.lead_email.toLowerCase().includes(q) ||
      (e.lead_company?.toLowerCase().includes(q) ?? false)
    );
  });

  const approvedCount = emails.filter((e) => e.status === "approved").length;

  const deleteMutation = useMutation({
    mutationFn: () => deleteCampaign(id ?? ""),
    onSuccess() {
      void queryClient.invalidateQueries({ queryKey: ["campaigns"] });
      toast.success("Campaign deleted.");
      void navigate("/campaigns");
    },
    onError() {
      toast.error("Failed to delete campaign.");
    },
  });

  if (isPending) {
    return (
      <div className="space-y-4 max-w-3xl">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-60 w-full" />
      </div>
    );
  }

  if (isError || !campaign) {
    return (
      <div className="rounded-md border border-destructive/50 bg-destructive/5 p-4 text-sm text-destructive max-w-lg">
        Failed to load campaign. It may have been deleted.
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-3xl">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => void navigate("/campaigns")}
            aria-label="Back to campaigns"
            className="mt-0.5 shrink-0"
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div className="space-y-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-semibold break-all">
                {campaign.name}
              </h1>
              <CampaignStatusBadge status={campaign.status} />
            </div>
            <p className="text-xs text-muted-foreground">
              Created {fullDateTime(campaign.created_at)}
            </p>
          </div>
        </div>

        {/* Delete */}
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button variant="outline" size="sm" className="shrink-0 gap-2">
              <Trash2 className="h-4 w-4" />
              Delete
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Delete campaign?</AlertDialogTitle>
              <AlertDialogDescription>
                This will permanently delete &quot;{campaign.name}&quot; and all
                its leads and generated emails. This cannot be undone.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction
                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                onClick={() => deleteMutation.mutate()}
                disabled={deleteMutation.isPending}
              >
                Delete
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="leads">Leads</TabsTrigger>
          <TabsTrigger value="emails">Emails</TabsTrigger>
          <TabsTrigger value="metrics">Metrics</TabsTrigger>
        </TabsList>

        {/* Overview tab */}
        <TabsContent value="overview" className="space-y-4 pt-4">
          <CampaignProgress campaign={campaign} />

          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">
                Campaign Info
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div className="flex justify-between gap-4">
                <span className="text-muted-foreground shrink-0">Name</span>
                <span className="text-right break-all">{campaign.name}</span>
              </div>
              <Separator />
              <div className="flex justify-between gap-4">
                <span className="text-muted-foreground shrink-0">CSV file</span>
                <span className="text-right truncate">
                  {campaign.csv_filename ?? "—"}
                </span>
              </div>
              <Separator />
              <div className="flex justify-between gap-4">
                <span className="text-muted-foreground shrink-0">
                  Total leads
                </span>
                <span className="tabular-nums">{campaign.total_leads}</span>
              </div>
              <Separator />
              <div className="flex justify-between gap-4">
                <span className="text-muted-foreground shrink-0">Created</span>
                <span className="text-right">
                  {fullDateTime(campaign.created_at)}
                </span>
              </div>
              <Separator />
              <div className="flex justify-between gap-4">
                <span className="text-muted-foreground shrink-0">Updated</span>
                <span className="text-right">
                  {fullDateTime(campaign.updated_at)}
                </span>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Leads tab */}
        <TabsContent value="leads" className="pt-4">
          <LeadsTable
            campaignId={campaign.id}
            campaignStatus={campaign.status}
          />
        </TabsContent>

        {/* Emails tab */}
        <TabsContent value="emails" className="space-y-4 pt-4">
          {/* Toolbar */}
          <div className="flex items-center gap-3">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
              <Input
                placeholder="Search emails…"
                value={emailSearch}
                onChange={(e) => setEmailSearch(e.target.value)}
                className="pl-8"
              />
            </div>
            <Button
              size="sm"
              className="gap-2 shrink-0"
              disabled={approvedCount === 0}
              onClick={() => setBulkSendOpen(true)}
            >
              <Send className="h-4 w-4" />
              Send all approved
              {approvedCount > 0 && (
                <span className="ml-1 rounded-full bg-primary-foreground/20 px-1.5 text-xs tabular-nums">
                  {approvedCount}
                </span>
              )}
            </Button>
          </div>

          {/* Skeleton */}
          {emailsPending && (
            <div className="space-y-3">
              {[1, 2, 3].map((n) => (
                <Skeleton key={n} className="h-32 w-full" />
              ))}
            </div>
          )}

          {/* Empty state */}
          {!emailsPending && filteredEmails.length === 0 && (
            <EmptyState
              icon={Mail}
              title={
                emailSearch ? "No emails match your search" : "No emails yet"
              }
              description={
                emailSearch
                  ? "Try a different name, email, or company."
                  : "Emails will appear here once the pipeline has generated drafts."
              }
            />
          )}

          {/* Email cards */}
          {!emailsPending && filteredEmails.length > 0 && (
            <div className="space-y-3">
              {filteredEmails.map((email) => (
                <EmailReviewCard
                  key={email.id}
                  email={email}
                  campaignId={campaign.id}
                />
              ))}
            </div>
          )}

          <BulkSendDialog
            open={bulkSendOpen}
            onClose={() => setBulkSendOpen(false)}
            campaignId={campaign.id}
            emails={emails}
          />
        </TabsContent>

        {/* Metrics tab */}
        <TabsContent value="metrics" className="space-y-6 pt-4">
          <StatsCards campaign={campaign} />

          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">
                Pipeline Funnel
              </CardTitle>
            </CardHeader>
            <CardContent>
              <CampaignFunnel campaign={campaign} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">Open Rate</CardTitle>
            </CardHeader>
            <CardContent>
              <OpenRateChart campaign={campaign} />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
