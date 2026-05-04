import type { ConnectivityState } from "../hooks/useNetworkAndApiStatus";

const LABEL: Record<ConnectivityState, string> = {
  checking: "Checking connection…",
  offline: "You are offline",
  "no-api-base": "API base URL not configured",
  ready: "Connected",
  "api-unavailable": "Server unavailable — try again soon",
};

export function NetworkStatusBar({ status }: { status: ConnectivityState }) {
  return (
    <div
      className="network-status-bar"
      data-testid="network-status"
      data-status={status}
      role="status"
      aria-live="polite"
    >
      {LABEL[status]}
    </div>
  );
}
