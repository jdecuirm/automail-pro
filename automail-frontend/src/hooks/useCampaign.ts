import { useQuery } from "@tanstack/react-query";
import { getCampaign } from "@/api/campaigns";
import type { CampaignResponse } from "@/types/api";
import { ACTIVE_CAMPAIGN_STATUSES } from "@/lib/constants";

export function useCampaign(id: string) {
  return useQuery<CampaignResponse>({
    queryKey: ["campaign", id],
    queryFn: () => getCampaign(id),
    refetchInterval(query) {
      const status = query.state.data?.status;
      if (status && ACTIVE_CAMPAIGN_STATUSES.has(status)) return 3_000;
      return false;
    },
  });
}
