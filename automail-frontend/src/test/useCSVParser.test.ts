import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { useCSVParser } from "@/hooks/useCSVParser";

// Silence sonner toasts in tests
vi.mock("sonner", () => ({ toast: { error: vi.fn(), success: vi.fn() } }));

// Minimal PapaParse mock so parseCSVPreview resolves for valid files
vi.mock("@/lib/csv", () => ({
  parseCSVPreview: vi.fn().mockResolvedValue({
    headers: ["name", "email"],
    rows: [],
    totalRows: 0,
    errors: [],
  }),
}));

function makeFile(name: string, type: string, content = "name,email\n") {
  return new File([content], name, { type });
}

describe("useCSVParser — MIME validation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("rejects a file with a non-.csv extension", async () => {
    const { result } = renderHook(() => useCSVParser());
    const pdf = makeFile("report.pdf", "application/pdf");
    await act(async () => {
      await result.current.parse(pdf);
    });
    expect(result.current.fileError).toContain("Only CSV files are accepted");
    expect(result.current.result).toBeNull();
  });

  it("rejects a .csv file whose MIME type is application/pdf", async () => {
    const { result } = renderHook(() => useCSVParser());
    // Extension is .csv but MIME is wrong — simulates a renamed PDF
    const renamed = makeFile("leads.csv", "application/pdf");
    await act(async () => {
      await result.current.parse(renamed);
    });
    expect(result.current.fileError).toContain("application/pdf");
    expect(result.current.result).toBeNull();
  });

  it("accepts a file with text/csv MIME type", async () => {
    const { result } = renderHook(() => useCSVParser());
    const csv = makeFile("leads.csv", "text/csv");
    await act(async () => {
      await result.current.parse(csv);
    });
    expect(result.current.fileError).toBeNull();
    expect(result.current.result).not.toBeNull();
  });

  it("accepts a .csv file with text/plain MIME (common on some systems)", async () => {
    const { result } = renderHook(() => useCSVParser());
    const csv = makeFile("leads.csv", "text/plain");
    await act(async () => {
      await result.current.parse(csv);
    });
    expect(result.current.fileError).toBeNull();
    expect(result.current.result).not.toBeNull();
  });

  it("accepts a .csv file with application/vnd.ms-excel MIME", async () => {
    const { result } = renderHook(() => useCSVParser());
    const csv = makeFile("leads.csv", "application/vnd.ms-excel");
    await act(async () => {
      await result.current.parse(csv);
    });
    expect(result.current.fileError).toBeNull();
    expect(result.current.result).not.toBeNull();
  });

  it("rejects a .txt file (wrong extension)", async () => {
    const { result } = renderHook(() => useCSVParser());
    const txt = makeFile("data.txt", "text/plain");
    await act(async () => {
      await result.current.parse(txt);
    });
    expect(result.current.fileError).toContain("Only CSV files are accepted");
  });
});
