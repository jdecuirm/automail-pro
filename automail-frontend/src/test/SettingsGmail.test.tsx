import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { beforeAll, afterAll, afterEach, describe, expect, it } from "vitest";
import SettingsGmail from "@/routes/Settings/Gmail";

// MSW server — default handler: disconnected state
const server = setupServer(
  http.get("http://localhost:8000/api/oauth/google/status", () => {
    return HttpResponse.json({
      connected: false,
      email_address: null,
      needs_reconnect: false,
    });
  }),
);

beforeAll(() => {
  server.listen();
});
afterEach(() => {
  server.resetHandlers();
});
afterAll(() => {
  server.close();
});

function renderGmailSettings(initialPath = "/settings/gmail") {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route path="/settings/gmail" element={<SettingsGmail />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("SettingsGmail", () => {
  it("shows connect card when Gmail is disconnected", async () => {
    renderGmailSettings();
    await waitFor(() => {
      expect(screen.getByText("Connect with Google")).toBeInTheDocument();
    });
  });

  it("shows connected state with email when Gmail is connected", async () => {
    server.use(
      http.get("http://localhost:8000/api/oauth/google/status", () => {
        return HttpResponse.json({
          connected: true,
          email_address: "user@example.com",
          needs_reconnect: false,
        });
      }),
    );
    renderGmailSettings();
    await waitFor(() => {
      expect(screen.getByText("user@example.com")).toBeInTheDocument();
      expect(screen.getByText("Connected")).toBeInTheDocument();
    });
  });

  it("shows reconnect warning when needs_reconnect is true", async () => {
    server.use(
      http.get("http://localhost:8000/api/oauth/google/status", () => {
        return HttpResponse.json({
          connected: true,
          email_address: "user@example.com",
          needs_reconnect: true,
        });
      }),
    );
    renderGmailSettings();
    await waitFor(() => {
      expect(screen.getByText(/credentials have expired/i)).toBeInTheDocument();
    });
  });

  it("shows disconnect button when connected", async () => {
    server.use(
      http.get("http://localhost:8000/api/oauth/google/status", () => {
        return HttpResponse.json({
          connected: true,
          email_address: "user@example.com",
          needs_reconnect: false,
        });
      }),
    );
    renderGmailSettings();
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /disconnect gmail/i }),
      ).toBeInTheDocument();
    });
  });

  it("renders skeleton loading state initially", () => {
    renderGmailSettings();
    // While query is pending, the skeleton is shown and the main content is NOT
    expect(screen.queryByText("Connect with Google")).not.toBeInTheDocument();
  });
});
