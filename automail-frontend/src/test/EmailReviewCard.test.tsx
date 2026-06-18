import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect } from "vitest";
import EmailReviewCard from "@/components/emails/EmailReviewCard";
import type { EmailResponse } from "@/types/api";

const DRAFT_EMAIL: EmailResponse = {
  id: "e1",
  lead_id: "l1",
  lead_name: "Alice Smith",
  lead_email: "alice@acme.com",
  lead_company: "Acme Corp",
  subject: "Quick question about Acme Corp",
  body_text: "Hi Alice,\n\nI saw your work.\n\nBest,\nJorge",
  body_html: "<p>Hi Alice,</p>",
  status: "draft",
  sent_at: null,
  gmail_message_id: null,
  error_message: null,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

const SENT_EMAIL: EmailResponse = {
  ...DRAFT_EMAIL,
  id: "e2",
  status: "sent",
  sent_at: new Date().toISOString(),
  gmail_message_id: "msg123abc",
};

const FAILED_EMAIL: EmailResponse = {
  ...DRAFT_EMAIL,
  id: "e3",
  status: "failed",
  error_message: "Gmail quota exceeded",
};

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe("EmailReviewCard", () => {
  it("renders lead name and subject", () => {
    render(<EmailReviewCard email={DRAFT_EMAIL} campaignId="c1" />, {
      wrapper,
    });
    expect(screen.getByText("Alice Smith")).toBeInTheDocument();
    expect(
      screen.getByText("Quick question about Acme Corp"),
    ).toBeInTheDocument();
  });

  it("shows Approve, Edit, Reject buttons for draft status", () => {
    render(<EmailReviewCard email={DRAFT_EMAIL} campaignId="c1" />, {
      wrapper,
    });
    expect(
      screen.getByRole("button", { name: /approve/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /edit/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /reject/i })).toBeInTheDocument();
  });

  it("does NOT show action buttons for sent emails", () => {
    render(<EmailReviewCard email={SENT_EMAIL} campaignId="c1" />, { wrapper });
    expect(
      screen.queryByRole("button", { name: /approve/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /reject/i }),
    ).not.toBeInTheDocument();
  });

  it("shows error message for failed emails", () => {
    render(<EmailReviewCard email={FAILED_EMAIL} campaignId="c1" />, {
      wrapper,
    });
    expect(screen.getByText("Gmail quota exceeded")).toBeInTheDocument();
  });

  it("shows lead email in subtitle", () => {
    render(<EmailReviewCard email={DRAFT_EMAIL} campaignId="c1" />, {
      wrapper,
    });
    expect(screen.getByText(/alice@acme\.com/)).toBeInTheDocument();
  });
});
