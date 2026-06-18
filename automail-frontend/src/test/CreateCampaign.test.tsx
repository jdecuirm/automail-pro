import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import CreateCampaign from "@/routes/Campaigns/Create";

function renderCreate() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={["/campaigns/new"]}>
        <Routes>
          <Route path="/campaigns/new" element={<CreateCampaign />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("CreateCampaign form validation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the name input", () => {
    renderCreate();
    expect(screen.getByPlaceholderText(/SaaS Founders/i)).toBeInTheDocument();
  });

  it("submit button is disabled with empty name", () => {
    renderCreate();
    const btn = screen.getByRole("button", {
      name: /create campaign/i,
    });
    expect(btn).toBeDisabled();
  });

  it("submit button is disabled without CSV file even with name filled", async () => {
    renderCreate();
    const nameInput = screen.getByPlaceholderText(/SaaS Founders/i);
    fireEvent.change(nameInput, { target: { value: "My Campaign" } });
    await waitFor(() => {
      const btn = screen.getByRole("button", { name: /create campaign/i });
      expect(btn).toBeDisabled();
    });
  });

  it("shows CSV upload zone", () => {
    renderCreate();
    expect(screen.getByLabelText(/upload csv file/i)).toBeInTheDocument();
  });
});
