import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi } from "vitest";
import CommandPalette from "@/components/common/CommandPalette";

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

describe("CommandPalette", () => {
  it("renders without crash when open=true", () => {
    render(<CommandPalette open={true} onOpenChange={() => undefined} />, {
      wrapper,
    });
    expect(screen.getByPlaceholderText(/type a command/i)).toBeInTheDocument();
  });

  it("shows navigation items", () => {
    render(<CommandPalette open={true} onOpenChange={() => undefined} />, {
      wrapper,
    });
    expect(screen.getByText("Go to Dashboard")).toBeInTheDocument();
    expect(screen.getByText("Go to Campaigns")).toBeInTheDocument();
    expect(screen.getByText("Go to Settings")).toBeInTheDocument();
  });

  it("shows quick action items", () => {
    render(<CommandPalette open={true} onOpenChange={() => undefined} />, {
      wrapper,
    });
    expect(screen.getByText("Create new campaign")).toBeInTheDocument();
    expect(screen.getByText("Toggle theme")).toBeInTheDocument();
  });

  it("calls onOpenChange with false when Escape is pressed inside dialog", () => {
    const onOpenChange = vi.fn();
    render(<CommandPalette open={true} onOpenChange={onOpenChange} />, {
      wrapper,
    });
    const dialog = document.querySelector("[role='dialog']");
    if (dialog) {
      fireEvent.keyDown(dialog, { key: "Escape" });
    }
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });
});
