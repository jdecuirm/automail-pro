// Smoke test — verifies the Vitest + jsdom + jest-dom harness is wired correctly.
// Real component tests will live in src/components/**/*.test.tsx

import { describe, it, expect } from "vitest";

describe("test harness", () => {
  it("runs in jsdom environment", () => {
    expect(typeof window).toBe("object");
  });

  it("jest-dom matchers are available", () => {
    const el = document.createElement("button");
    el.textContent = "Click me";
    document.body.appendChild(el);
    expect(el).toBeInTheDocument();
    document.body.removeChild(el);
  });
});
