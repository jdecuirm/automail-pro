import type { CampaignStatus } from "@/types/api";

/**
 * Campaign statuses that indicate active pipeline work — triggers polling in hooks.
 * "review" included: campaigns in review still benefit from real-time updates
 * (worker may auto-advance them after all emails draft).
 */
export const ACTIVE_CAMPAIGN_STATUSES = new Set<CampaignStatus>([
  "uploaded",
  "scraping",
  "generating",
  "review",
  "sending",
]);
