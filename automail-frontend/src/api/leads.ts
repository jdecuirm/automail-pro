import type { LeadPagination, LeadResponse } from "@/types/api";
import { apiGet } from "./client";

export interface ListLeadsParams {
  page?: number;
  page_size?: number;
  status?: string;
  search?: string;
}

export async function listLeads(
  campaignId: string,
  params: ListLeadsParams = {},
): Promise<LeadPagination> {
  const query = new URLSearchParams();
  if (params.page !== undefined) query.set("page", String(params.page));
  if (params.page_size !== undefined)
    query.set("page_size", String(params.page_size));
  if (params.status) query.set("status", params.status);
  if (params.search) query.set("search", params.search);

  const qs = query.toString();
  return apiGet<LeadPagination>(
    `/api/campaigns/${campaignId}/leads${qs ? `?${qs}` : ""}`,
  );
}

export async function getLead(id: string): Promise<LeadResponse> {
  return apiGet<LeadResponse>(`/api/leads/${id}`);
}
