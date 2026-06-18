import type {
  CampaignListItem,
  CampaignResponse,
  CSVUploadResponse,
} from "@/types/api";
import { apiDelete, apiGet, apiPostForm } from "./client";

export async function listCampaigns(): Promise<CampaignListItem[]> {
  return apiGet<CampaignListItem[]>("/api/campaigns");
}

export async function getCampaign(id: string): Promise<CampaignResponse> {
  return apiGet<CampaignResponse>(`/api/campaigns/${id}`);
}

export async function createCampaign(
  formData: FormData,
): Promise<CSVUploadResponse> {
  return apiPostForm<CSVUploadResponse>("/api/campaigns", formData);
}

export async function deleteCampaign(id: string): Promise<void> {
  return apiDelete(`/api/campaigns/${id}`);
}
