import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, apiGet, apiPost, apiDelete } from "@/api/client";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

describe("apiGet", () => {
  beforeEach(() => {
    fetchMock.mockReset();
  });

  it("returns parsed JSON on 200", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ hello: "world" }),
    });
    const result = await apiGet<{ hello: string }>("/test");
    expect(result).toEqual({ hello: "world" });
  });

  it("throws ApiError with status on non-ok response", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: () => Promise.resolve({ detail: "Not found" }),
    });
    await expect(apiGet("/missing")).rejects.toThrow(ApiError);

    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: () => Promise.resolve({ detail: "Not found" }),
    });
    await expect(apiGet("/missing")).rejects.toMatchObject({ status: 404 });
  });

  it("returns undefined on 204", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      status: 204,
      json: () => Promise.resolve(null),
    });
    const result = await apiDelete("/item/1");
    expect(result).toBeUndefined();
  });
});

describe("apiPost", () => {
  beforeEach(() => {
    fetchMock.mockReset();
  });

  it("sends JSON body with correct Content-Type", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ id: "1" }),
    });
    await apiPost("/endpoint", { key: "value" });
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/endpoint"),
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key: "value" }),
      }),
    );
  });
});
