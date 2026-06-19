import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import StatsCards from "@/components/metrics/StatsCards";
import type { CampaignStats } from "@/types/api";

const STATS: CampaignStats = {
  uploaded: 0,
  scraping: 0,
  researched: 0,
  generating: 0,
  drafted: 2,
  approved: 0,
  rejected: 1,
  sending: 0,
  sent: 5,
  opened: 2,
  failed: 0,
};

describe("StatsCards", () => {
  it("renders total leads", () => {
    render(<StatsCards stats={STATS} totalLeads={10} />);
    expect(screen.getByText("10")).toBeInTheDocument();
  });

  it("calculates open rate correctly (opened=2, sent+opened=7 → 29%)", () => {
    render(<StatsCards stats={STATS} totalLeads={10} />);
    // sent=5, opened=2 → total delivered = 7 → Math.round(2/7*100) = 29%
    expect(screen.getByText("29%")).toBeInTheDocument();
  });

  it("shows dash for open rate when nothing sent", () => {
    const noSentStats: CampaignStats = { ...STATS, sent: 0, opened: 0 };
    render(<StatsCards stats={noSentStats} totalLeads={10} />);
    expect(screen.getByText("—")).toBeInTheDocument();
  });
});
