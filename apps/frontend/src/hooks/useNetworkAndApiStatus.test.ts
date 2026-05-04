import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useNetworkAndApiStatus } from "./useNetworkAndApiStatus";

describe("useNetworkAndApiStatus", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
    Object.defineProperty(navigator, "onLine", {
      configurable: true,
      value: true,
    });
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  it("returns no-api-base when VITE_API_BASE_URL is empty", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "");

    const { result } = renderHook(() => useNetworkAndApiStatus());

    await waitFor(() => {
      expect(result.current).toBe("no-api-base");
    });
  });

  it("returns ready when health responds with status ok", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "http://localhost:18080");

    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ status: "ok", postgres: "reachable" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const { result } = renderHook(() => useNetworkAndApiStatus());

    await waitFor(() => {
      expect(result.current).toBe("ready");
    });

    expect(fetch).toHaveBeenCalledTimes(1);
    const call = vi.mocked(fetch).mock.calls[0];
    expect(call?.[0]).toBeInstanceOf(Request);
    expect((call?.[0] as Request).url).toBe("http://localhost:18080/health");
    expect((call?.[0] as Request).method).toBe("GET");
  });

  it("returns api-unavailable when health is degraded", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "http://localhost:18080");

    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify({ status: "degraded", postgres: "unreachable" }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );

    const { result } = renderHook(() => useNetworkAndApiStatus());

    await waitFor(() => {
      expect(result.current).toBe("api-unavailable");
    });
  });

  it("returns offline when navigator reports offline", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "http://localhost:18080");

    Object.defineProperty(navigator, "onLine", {
      configurable: true,
      value: false,
    });

    const { result } = renderHook(() => useNetworkAndApiStatus());

    expect(result.current).toBe("offline");
    expect(fetch).not.toHaveBeenCalled();
  });
});
