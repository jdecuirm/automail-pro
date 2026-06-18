import { useQuery } from "@tanstack/react-query";
import { listLeads } from "@/api/leads";
import type { LeadPagination, CampaignStatus } from "@/types/api";
import type { ListLeadsParams } from "@/api/leads";

const ACTIVE_STATUSES: CampaignStatus[] = [
  "uploaded",
  "scraping",
  "generating",
  "sending",
];

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
      if (campaignStatus && ACTIVE_STATUSES.includes(campaignStatus))
        return 5_000;
      return false;
    },
  });
}
