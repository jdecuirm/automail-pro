import type { GmailStatusResponse } from "@/types/api";
import { apiDelete, apiGet } from "./client";

export async function getGmailStatus(): Promise<GmailStatusResponse> {
  return apiGet<GmailStatusResponse>("/api/oauth/google/status");
}

export async function disconnectGmail(): Promise<void> {
  return apiDelete("/api/oauth/google/disconnect");
}
