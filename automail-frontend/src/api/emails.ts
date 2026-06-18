import { apiGet, apiPost, apiPatch } from "@/api/client";
import type {
  EmailResponse,
  EmailUpdateRequest,
  BulkSendResponse,
} from "@/types/api";

export async function listCampaignEmails(
  campaignId: string,
): Promise<EmailResponse[]> {
  return apiGet<EmailResponse[]>(`/api/campaigns/${campaignId}/emails`);
}

export async function getEmail(id: string): Promise<EmailResponse> {
  return apiGet<EmailResponse>(`/api/emails/${id}`);
}

export async function approveEmail(id: string): Promise<EmailResponse> {
  return apiPost<EmailResponse>(`/api/emails/${id}/approve`);
}

export async function rejectEmail(id: string): Promise<EmailResponse> {
  return apiPost<EmailResponse>(`/api/emails/${id}/reject`);
}

export async function updateEmail(
  id: string,
  data: EmailUpdateRequest,
): Promise<EmailResponse> {
  return apiPatch<EmailResponse>(`/api/emails/${id}`, data);
}

export async function bulkSendApproved(
  campaignId: string,
): Promise<BulkSendResponse> {
  return apiPost<BulkSendResponse>(
    `/api/campaigns/${campaignId}/send-approved`,
  );
}
