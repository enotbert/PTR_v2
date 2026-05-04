import { useCallback, useEffect, useMemo, useRef, useState } from "react";

export type ConnectivityState =
  | "checking"
  | "offline"
  | "no-api-base"
  | "ready"
  | "api-unavailable";

const HEALTH_PATH = "/health";
const CHECK_TIMEOUT_MS = 6000;
const RECHECK_MS = 30_000;

function normalizeApiBase(raw: string): string {
  return raw.trim().replace(/\/+$/, "");
}

function healthUrl(apiBase: string): string {
  return `${normalizeApiBase(apiBase)}${HEALTH_PATH}`;
}

async function fetchHealthStatus(
  apiBase: string,
  signal: AbortSignal,
): Promise<"ok" | "degraded" | "fail"> {
  const url = healthUrl(apiBase);
  try {
    const res = await fetch(url, {
      method: "GET",
      signal,
      credentials: "omit",
      cache: "no-store",
    });
    if (!res.ok) {
      return "fail";
    }
    const data: unknown = await res.json();
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

  useEffect(() => {
    runIdRef.current += 1;
    const id = runIdRef.current;
    void checkNow(id);
    return () => {
      abortRef.current?.abort();
      abortRef.current = null;
    };
  }, [apiBase, browserOnline, checkNow]);

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
