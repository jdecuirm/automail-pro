import { useQuery } from "@tanstack/react-query";
import { getGmailStatus } from "@/api/oauth";
import type { GmailStatusResponse } from "@/types/api";

export function useGmailStatus() {
  return useQuery<GmailStatusResponse>({
    queryKey: ["gmail-status"],
    queryFn: getGmailStatus,
    refetchOnWindowFocus: true,
    refetchInterval: 30_000,
  });
}
