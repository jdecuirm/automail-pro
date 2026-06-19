import { useQuery } from "@tanstack/react-query";
import { listLeads } from "@/api/leads";
import type { LeadPagination, CampaignStatus } from "@/types/api";
import type { ListLeadsParams } from "@/api/leads";
import { ACTIVE_CAMPAIGN_STATUSES } from "@/lib/constants";

export function useCampaignLeads(
  campaignId: string,
  params: ListLeadsParams = {},
  campaignStatus?: CampaignStatus,
) {
  return useQuery<LeadPagination>({
    queryKey: ["campaign-leads", campaignId, params],
    queryFn: () => listLeads(campaignId, params),
    placeholderData: (prev) => prev,
    refetchInterval() {
      if (campaignStatus && ACTIVE_CAMPAIGN_STATUSES.has(campaignStatus))
        return 5_000;
      return false;
    },
  });
}
