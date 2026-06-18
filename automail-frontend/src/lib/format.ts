import { formatDistanceToNow, format } from "date-fns";
import type { CampaignStats } from "@/types/api";

export function relativeTime(isoString: string): string {
  return formatDistanceToNow(new Date(isoString), { addSuffix: true });
}

export function fullDateTime(isoString: string): string {
  return format(new Date(isoString), "MMM d, yyyy 'at' h:mm a");
}

export function fileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function getDefaultStats(): CampaignStats {
  return {
    uploaded: 0,
    scraping: 0,
    researched: 0,
    generating: 0,
    drafted: 0,
    approved: 0,
    rejected: 0,
    sending: 0,
    sent: 0,
    opened: 0,
    failed: 0,
  };
}

export function mergeStats(
  raw: Partial<CampaignStats> | null | undefined,
): CampaignStats {
  return { ...getDefaultStats(), ...(raw ?? {}) };
}
