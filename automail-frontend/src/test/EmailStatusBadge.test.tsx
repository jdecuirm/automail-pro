import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import EmailStatusBadge from "@/components/emails/EmailStatusBadge";

describe("EmailStatusBadge", () => {
  it("renders Draft", () => {
    render(<EmailStatusBadge status="draft" />);
    expect(screen.getByText("Draft")).toBeInTheDocument();
  });

  it("renders Approved", () => {
    render(<EmailStatusBadge status="approved" />);
    expect(screen.getByText("Approved")).toBeInTheDocument();
  });

  it("renders Sent", () => {
    render(<EmailStatusBadge status="sent" />);
    expect(screen.getByText("Sent")).toBeInTheDocument();
  });

  it("renders Failed", () => {
    render(<EmailStatusBadge status="failed" />);
    expect(screen.getByText("Failed")).toBeInTheDocument();
  });

  it("renders Rejected", () => {
    render(<EmailStatusBadge status="rejected" />);
    expect(screen.getByText("Rejected")).toBeInTheDocument();
  });
});
