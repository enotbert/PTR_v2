import type { ReactNode } from "react";
import type { ConnectivityState } from "../hooks/useNetworkAndApiStatus";
import { NetworkStatusBar } from "./NetworkStatusBar";

type Props = {
  connectivity: ConnectivityState;
  children: ReactNode;
};

export function AppShell({ connectivity, children }: Props) {
  return (
    <div className="app-shell">
      <header className="app-shell__header">
        <NetworkStatusBar status={connectivity} />
      </header>
      <main className="app-shell__main">{children}</main>
    </div>
  );
}
