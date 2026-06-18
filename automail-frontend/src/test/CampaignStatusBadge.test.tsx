import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import CampaignStatusBadge from "@/components/campaigns/CampaignStatusBadge";

describe("CampaignStatusBadge", () => {
  it("renders 'Completed' for completed status", () => {
    render(<CampaignStatusBadge status="completed" />);
    expect(screen.getByText("Completed")).toBeInTheDocument();
  });

  it("renders 'Scraping' for scraping status", () => {
    render(<CampaignStatusBadge status="scraping" />);
    expect(screen.getByText("Scraping")).toBeInTheDocument();
  });

  it("renders 'Failed' for failed status", () => {
    render(<CampaignStatusBadge status="failed" />);
    expect(screen.getByText("Failed")).toBeInTheDocument();
  });
});
