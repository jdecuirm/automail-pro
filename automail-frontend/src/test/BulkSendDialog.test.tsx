import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect } from "vitest";
import BulkSendDialog from "@/components/emails/BulkSendDialog";

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
    render(
      <BulkSendDialog
        open={true}
        onClose={() => undefined}
        campaignId="c1"
        approvedCount={2}
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
    render(
      <BulkSendDialog
        open={true}
        onClose={() => undefined}
        campaignId="c1"
        approvedCount={51}
        profileComplete={true}
      />,
      { wrapper },
    );
    expect(
      screen.getByText(/50 emails will be sent today/i),
    ).toBeInTheDocument();
  });

  it("send button shows approved count", () => {
    render(
      <BulkSendDialog
        open={true}
        onClose={() => undefined}
        campaignId="c1"
        approvedCount={1}
        profileComplete={true}
      />,
      { wrapper },
    );
    expect(
      screen.getByRole("button", { name: /send 1 email/i }),
    ).toBeInTheDocument();
  });
});
