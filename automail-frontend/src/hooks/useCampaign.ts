import { useQuery } from "@tanstack/react-query";
import { getCampaign } from "@/api/campaigns";
import type { CampaignResponse, CampaignStatus } from "@/types/api";

const ACTIVE_STATUSES: CampaignStatus[] = [
  "uploaded",
  "scraping",
  "generating",
  "review", // campaign can still move to "completed" while emails are being sent
  "sending",
];

export function useCampaign(id: string) {
  return useQuery<CampaignResponse>({
    queryKey: ["campaign", id],
    queryFn: () => getCampaign(id),
    refetchInterval(query) {
      const status = query.state.data?.status;
      if (status && ACTIVE_STATUSES.includes(status)) return 3_000;
      return false;
    },
  });
}
