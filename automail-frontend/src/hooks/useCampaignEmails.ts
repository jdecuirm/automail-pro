import { useQuery } from "@tanstack/react-query";
import { listCampaignEmails } from "@/api/emails";
import type { CampaignStatus } from "@/types/api";

const ACTIVE_STATUSES = new Set<CampaignStatus>(["generating", "review"]);

export function useCampaignEmails(
  campaignId: string,
  campaignStatus?: CampaignStatus,
) {
  const isActive = campaignStatus ? ACTIVE_STATUSES.has(campaignStatus) : false;

  return useQuery({
    queryKey: ["campaign-emails", campaignId],
    queryFn: () => listCampaignEmails(campaignId),
    enabled: !!campaignId,
    staleTime: 15_000,
    refetchInterval: isActive ? 3_000 : false,
  });
}
