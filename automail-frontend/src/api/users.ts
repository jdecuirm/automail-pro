import type { UserProfile, UserProfileUpdate } from "@/types/api";

const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail?.detail ?? `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export function getProfile(): Promise<UserProfile> {
  return request<UserProfile>("/api/users/me");
}

export function updateProfile(data: UserProfileUpdate): Promise<UserProfile> {
  return request<UserProfile>("/api/users/me", {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}
