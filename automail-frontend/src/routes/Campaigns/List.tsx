import { useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { Plus, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import CampaignsTable from "@/components/campaigns/CampaignsTable";
import EmptyState from "@/components/common/EmptyState";
import { useCampaigns } from "@/hooks/useCampaigns";
import type { CampaignStatus } from "@/types/api";

const ALL_STATUSES: CampaignStatus[] = [
  "draft",
  "uploaded",
  "scraping",
  "generating",
  "review",
  "sending",
  "completed",
  "paused",
  "failed",
];

export default function CampaignList() {
  const navigate = useNavigate();
  const { data: campaigns, isPending, isError } = useCampaigns();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<CampaignStatus | "">("");

  const filtered = useMemo(() => {
    if (!campaigns) return [];
    return campaigns.filter((c) => {
      const matchesSearch = c.name.toLowerCase().includes(search.toLowerCase());
      const matchesStatus = statusFilter === "" || c.status === statusFilter;
      return matchesSearch && matchesStatus;
    });
  }, [campaigns, search, statusFilter]);

  const hasFilters = search !== "" || statusFilter !== "";

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Campaigns</h1>
          <p className="text-sm text-muted-foreground">
            Manage your outreach campaigns
          </p>
        </div>
        <Button onClick={() => void navigate("/campaigns/new")}>
          <Plus className="mr-2 h-4 w-4" />
          New Campaign
        </Button>
      </div>

      {/* Toolbar */}
      {!isPending && campaigns && campaigns.length > 0 && (
        <div className="flex flex-wrap items-center gap-3">
          <Input
            placeholder="Search campaigns…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="max-w-xs h-8 text-sm"
          />
          <select
            value={statusFilter}
            onChange={(e) =>
              setStatusFilter(e.target.value as CampaignStatus | "")
            }
            className="h-8 rounded-md border border-input bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          >
            <option value="">All statuses</option>
            {ALL_STATUSES.map((s) => (
              <option key={s} value={s}>
                {s.charAt(0).toUpperCase() + s.slice(1)}
              </option>
            ))}
          </select>
          {hasFilters && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setSearch("");
                setStatusFilter("");
              }}
              className="h-8 text-xs"
            >
              Reset filters
            </Button>
          )}
          <span className="text-xs text-muted-foreground ml-auto">
            {filtered.length} of {campaigns.length} campaigns
          </span>
        </div>
      )}

      {/* Content */}
      {isPending ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full rounded-md" />
          ))}
        </div>
      ) : isError ? (
        <div className="rounded-md border border-destructive/50 bg-destructive/5 p-4 text-sm text-destructive">
          Failed to load campaigns. Please refresh.
        </div>
      ) : campaigns && campaigns.length === 0 ? (
        <EmptyState
          icon={Send}
          title="No campaigns yet"
          description="Upload your first lead list to get started"
          action={{
            label: "Create your first campaign",
            onClick: () => void navigate("/campaigns/new"),
          }}
        />
      ) : (
        <CampaignsTable data={filtered} />
      )}
    </div>
  );
}
