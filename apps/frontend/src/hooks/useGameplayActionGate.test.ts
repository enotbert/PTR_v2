import { renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { useGameplayActionGate } from "./useGameplayActionGate";
import type { ConnectivityState } from "./useNetworkAndApiStatus";

describe("useGameplayActionGate", () => {
  it("blocks gameplay actions when connectivity is not ready", () => {
    const { result, rerender } = renderHook(
      ({ status }) => useGameplayActionGate(status),
      { initialProps: { status: "offline" as ConnectivityState } },
    );

    expect(result.current.blocked).toBe(true);
    expect(result.current.reason).toBe("offline");
    expect(result.current.message).toContain("require network connection");

    rerender({ status: "api-unavailable" as ConnectivityState });
    expect(result.current.blocked).toBe(true);
    expect(result.current.reason).toBe("api-unavailable");
  });

  it("runs action only when ready", () => {
    const blockedAction = vi.fn();
    const { result, rerender } = renderHook(
      ({ status }) => useGameplayActionGate(status),
      { initialProps: { status: "checking" as ConnectivityState } },
    );

    expect(result.current.runIfAllowed(blockedAction)).toBe(false);
    expect(blockedAction).not.toHaveBeenCalled();

    rerender({ status: "ready" as ConnectivityState });
    expect(result.current.runIfAllowed(blockedAction)).toBe(true);
    expect(blockedAction).toHaveBeenCalledTimes(1);
  });
});
