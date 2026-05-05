import { AppShell } from "./components/AppShell";
import { TavernHomeScreen } from "./components/TavernHomeScreen";
import { useGameplaySession } from "./hooks/useGameplaySession";
import { useNetworkAndApiStatus } from "./hooks/useNetworkAndApiStatus";

export default function App() {
  const connectivity = useNetworkAndApiStatus();
  const gameplaySession = useGameplaySession(connectivity);

  return (
    <AppShell connectivity={connectivity}>
      <TavernHomeScreen
        connectivity={connectivity}
        gameplaySession={gameplaySession}
      />
    </AppShell>
  );
}
