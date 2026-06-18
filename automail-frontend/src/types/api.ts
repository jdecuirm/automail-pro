// Backend Pydantic schemas mirrored in TypeScript.
// snake_case preserved (no transform).
// erasableSyntaxOnly: no enum — use union types only.

export type CampaignStatus =
  | "draft"
  | "scraping"
  | "generating"
  | "review"
  | "sending";

export type LeadStatus =
  | "uploaded"
  | "scraping"
  | "researched"
  | "generating"
  | "drafted"
  | "approved"
  | "rejected"
  | "sending"
  | "sent"
  | "opened";

export type EmailStatus =
  | "draft"
  | "approved"
  | "rejected"
  | "sending"
  | "sent"
  | "failed";

// OAuth / Gmail
export interface GmailStatusResponse {
  connected: boolean;
  email_address: string | null;
  needs_reconnect: boolean;
}

// Campaigns (used in I.2+, defined here for completeness)
export interface CampaignListItem {
  id: string;
  name: string;
  status: CampaignStatus;
  total_leads: number;
  created_at: string;
}

export interface CampaignResponse {
  id: string;
  name: string;
  status: CampaignStatus;
  csv_filename: string | null;
  total_leads: number;
  created_at: string;
  updated_at: string;
}

export interface CSVUploadResponse {
  campaign_id: string;
  total_rows: number;
  valid_leads: number;
  invalid_leads: number;
  validation_errors: Array<{
    row_number: number;
    error: string;
    raw_data: Record<string, string>;
  }>;
}

// Leads (used in I.2+)
export interface LeadResponse {
  id: string;
  name: string;
  email: string;
  company: string | null;
  website: string | null;
  linkedin_url: string | null;
  status: LeadStatus;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface LeadPagination {
  items: LeadResponse[];
  total: number;
  page: number;
  page_size: number;
}

// Emails (used in I.3+)
export interface EmailResponse {
  id: string;
  lead_id: string;
  lead_name: string;
  subject: string;
  body_text: string;
  body_html: string;
  status: EmailStatus;
  sent_at: string | null;
  gmail_message_id: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface EmailUpdateRequest {
  subject?: string;
  body_html?: string;
  body_text?: string;
}

export interface BulkSendResponse {
  dispatched: number;
  blocked_by_quota: number;
  remaining_quota_today: number;
}
