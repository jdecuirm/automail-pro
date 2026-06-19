import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect } from "vitest";
import BulkSendDialog from "@/components/emails/BulkSendDialog";
import type { EmailResponse } from "@/types/api";

const BASE: EmailResponse = {
  id: "e1",
  lead_id: "l1",
  lead_name: "Alice",
  lead_email: "alice@test.com",
  lead_company: null,
  subject: "Hi",
  body_text: "body",
  body_html: "<p>body</p>",
  status: "approved",
  sent_at: null,
  gmail_message_id: null,
  error_message: null,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
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

describe("BulkSendDialog", () => {
  it("shows approved email count", () => {
    const emails = [BASE, { ...BASE, id: "e2" }];
    render(
      <BulkSendDialog
        open={true}
        onClose={() => undefined}
        campaignId="c1"
        emails={emails}
        profileComplete={true}
      />,
      { wrapper },
    );
    // The count lives in a child <span>, so narrow to the <p> by tag + textContent
    expect(
      screen.getByText(
        (_, el) =>
          el?.tagName === "P" && /2 approved email/i.test(el.textContent ?? ""),
      ),
    ).toBeInTheDocument();
  });

  it("shows quota warning when approved count exceeds 50", () => {
    const manyEmails = Array.from({ length: 51 }, (_, i) => ({
      ...BASE,
      id: `e${i}`,
    }));
    render(
      <BulkSendDialog
        open={true}
        onClose={() => undefined}
        campaignId="c1"
        emails={manyEmails}
        profileComplete={true}
      />,
      { wrapper },
    );
    expect(
      screen.getByText(/50 emails will be sent today/i),
    ).toBeInTheDocument();
  });

  it("send button shows approved count", () => {
    const emails = [BASE];
    render(
      <BulkSendDialog
        open={true}
        onClose={() => undefined}
        campaignId="c1"
        emails={emails}
        profileComplete={true}
      />,
      { wrapper },
    );
    expect(
      screen.getByRole("button", { name: /send 1 email/i }),
    ).toBeInTheDocument();
  });
});
