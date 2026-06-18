import { useQuery } from "@tanstack/react-query";
import { listCampaigns } from "@/api/campaigns";
import type { CampaignListItem } from "@/types/api";

export function useCampaigns() {
  return useQuery<CampaignListItem[]>({
    queryKey: ["campaigns"],
    queryFn: listCampaigns,
    staleTime: 30_000,
  });
}
