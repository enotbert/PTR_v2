import { AppShell } from "./components/AppShell";
import { TavernHomeScreen } from "./components/TavernHomeScreen";
import { useNetworkAndApiStatus } from "./hooks/useNetworkAndApiStatus";

export default function App() {
  const connectivity = useNetworkAndApiStatus();

  return (
    <AppShell connectivity={connectivity}>
      <TavernHomeScreen connectivity={connectivity} />
    </AppShell>
  );
}
