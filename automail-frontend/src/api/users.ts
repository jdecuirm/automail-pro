import type { UserProfile, UserProfileUpdate } from "@/types/api";
import { apiGet, apiPatch } from "./client";

export function getProfile(): Promise<UserProfile> {
  return apiGet<UserProfile>("/api/users/me");
}

export function updateProfile(data: UserProfileUpdate): Promise<UserProfile> {
  return apiPatch<UserProfile>("/api/users/me", data);
}
