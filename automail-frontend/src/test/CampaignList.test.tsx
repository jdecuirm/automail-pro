import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { beforeAll, afterAll, afterEach, describe, it, expect } from "vitest";
import CampaignList from "@/routes/Campaigns/List";
import type { CampaignListItem } from "@/types/api";

const MOCK_CAMPAIGNS: CampaignListItem[] = [
  {
    id: "1",
    name: "Alpha Campaign",
    status: "completed",
    total_leads: 10,
    csv_filename: "alpha.csv",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: "2",
    name: "Beta Campaign",
    status: "scraping",
    total_leads: 5,
    csv_filename: "beta.csv",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];

const server = setupServer(
  http.get("http://localhost:8000/api/campaigns", () =>
    HttpResponse.json(MOCK_CAMPAIGNS),
  ),
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function renderList() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <CampaignList />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("CampaignList", () => {
  it("shows skeleton while loading", () => {
    renderList();
    // Skeletons render before data arrives
    expect(document.querySelector(".animate-pulse")).toBeTruthy();
  });

  it("renders campaign names after load", async () => {
    renderList();
    await waitFor(() => {
      expect(screen.getByText("Alpha Campaign")).toBeInTheDocument();
      expect(screen.getByText("Beta Campaign")).toBeInTheDocument();
    });
  });

  it("filters campaigns by name search", async () => {
    renderList();
    await waitFor(() => screen.getByText("Alpha Campaign"));
    const input = screen.getByPlaceholderText(/search campaigns/i);
    fireEvent.change(input, { target: { value: "alpha" } });
    expect(screen.getByText("Alpha Campaign")).toBeInTheDocument();
    expect(screen.queryByText("Beta Campaign")).not.toBeInTheDocument();
  });

  it("filters campaigns by status", async () => {
    const user = userEvent.setup();
    renderList();
    await waitFor(() => screen.getByText("Alpha Campaign"));
    // Open the shadcn Select dropdown and pick "Scraping"
    await user.click(screen.getByRole("combobox"));
    await user.click(screen.getByRole("option", { name: "Scraping" }));
    expect(screen.queryByText("Alpha Campaign")).not.toBeInTheDocument();
    expect(screen.getByText("Beta Campaign")).toBeInTheDocument();
  });

  it("shows empty state when no campaigns", async () => {
    server.use(
      http.get("http://localhost:8000/api/campaigns", () =>
        HttpResponse.json([]),
      ),
    );
    renderList();
    await waitFor(() => {
      expect(screen.getByText("No campaigns yet")).toBeInTheDocument();
    });
  });

  it("shows reset button when filters are active", async () => {
    renderList();
    await waitFor(() => screen.getByText("Alpha Campaign"));
    const input = screen.getByPlaceholderText(/search campaigns/i);
    fireEvent.change(input, { target: { value: "test" } });
    expect(screen.getByRole("button", { name: /reset/i })).toBeInTheDocument();
  });
});
