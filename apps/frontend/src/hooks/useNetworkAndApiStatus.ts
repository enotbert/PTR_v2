import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { createApiClient } from "../api/client";

export type ConnectivityState =
  | "checking"
  | "offline"
  | "no-api-base"
  | "ready"
  | "api-unavailable";

const CHECK_TIMEOUT_MS = 6000;
const RECHECK_MS = 30_000;

async function fetchHealthStatus(
  apiBase: string,
  signal: AbortSignal,
): Promise<"ok" | "degraded" | "fail"> {
  const client = createApiClient(apiBase);
  try {
    const { data, error, response } = await client.GET("/health", { signal });
    if (error || !response?.ok) {
      return "fail";
    }
    if (
      data &&
      typeof data === "object" &&
      "status" in data &&
      (data as { status: string }).status === "ok"
    ) {
      return "ok";
    }
    return "degraded";
  } catch {
    return "fail";
  }
}

export function useNetworkAndApiStatus(): ConnectivityState {
  const apiBase = useMemo(
    () => import.meta.env.VITE_API_BASE_URL?.trim() ?? "",
    [],
  );

  const [browserOnline, setBrowserOnline] = useState(true);
  const [phase, setPhase] = useState<"checking" | "done">("checking");
  const [apiOk, setApiOk] = useState(false);

  const runIdRef = useRef(0);
  const abortRef = useRef<AbortController | null>(null);

  const checkNow = useCallback(
    async (localRun: number) => {
      abortRef.current?.abort();
      abortRef.current = null;

      if (!apiBase) {
        if (runIdRef.current !== localRun) {
          return;
        }
        setPhase("done");
        setApiOk(false);
        return;
      }
      if (!navigator.onLine) {
        if (runIdRef.current !== localRun) {
          return;
        }
        setPhase("done");
        setApiOk(false);
        return;
      }

      setPhase("checking");
      setApiOk(false);

      const ac = new AbortController();
      abortRef.current = ac;
      const tid = window.setTimeout(() => ac.abort(), CHECK_TIMEOUT_MS);

      try {
        const result = await fetchHealthStatus(apiBase, ac.signal);
        if (runIdRef.current !== localRun) {
          return;
        }
        setPhase("done");
        setApiOk(result === "ok");
      } finally {
        window.clearTimeout(tid);
      }
    },
    [apiBase],
  );

  useEffect(() => {
    const onChange = () => setBrowserOnline(navigator.onLine);
    window.addEventListener("online", onChange);
    window.addEventListener("offline", onChange);
    setBrowserOnline(navigator.onLine);
    return () => {
      window.removeEventListener("online", onChange);
      window.removeEventListener("offline", onChange);
    };
  }, []);

  // biome-ignore lint/correctness/useExhaustiveDependencies: include browserOnline so a new run starts when connectivity changes; checkNow only depends on apiBase
  useEffect(() => {
    runIdRef.current += 1;
    const id = runIdRef.current;
    void checkNow(id);
    return () => {
      abortRef.current?.abort();
      abortRef.current = null;
    };
  }, [checkNow, browserOnline]);

  useEffect(() => {
    if (!apiBase || !browserOnline) {
      return;
    }
    const interval = window.setInterval(() => {
      runIdRef.current += 1;
      const id = runIdRef.current;
      void checkNow(id);
    }, RECHECK_MS);
    return () => window.clearInterval(interval);
  }, [apiBase, browserOnline, checkNow]);

  if (!browserOnline) {
    return "offline";
  }
  if (!apiBase) {
    return "no-api-base";
  }
  if (phase === "checking") {
    return "checking";
  }
  if (apiOk) {
    return "ready";
  }
  return "api-unavailable";
}
