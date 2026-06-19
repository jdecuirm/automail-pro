import { useQuery } from "@tanstack/react-query";
import { listCampaignEmails } from "@/api/emails";
import type { CampaignStatus } from "@/types/api";
import { ACTIVE_CAMPAIGN_STATUSES } from "@/lib/constants";

export function useCampaignEmails(
  campaignId: string,
  campaignStatus?: CampaignStatus,
) {
  const isActive = campaignStatus
    ? ACTIVE_CAMPAIGN_STATUSES.has(campaignStatus)
    : false;

  return useQuery({
    queryKey: ["campaign-emails", campaignId],
    queryFn: () => listCampaignEmails(campaignId),
    enabled: !!campaignId,
    staleTime: 15_000,
    refetchInterval: isActive ? 3_000 : false,
  });
}
