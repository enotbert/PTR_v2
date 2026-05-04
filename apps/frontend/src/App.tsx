import { AppShell } from "./components/AppShell";
import { HomePlaceholder } from "./components/HomePlaceholder";
import { useNetworkAndApiStatus } from "./hooks/useNetworkAndApiStatus";

export default function App() {
  const connectivity = useNetworkAndApiStatus();

  return (
    <AppShell connectivity={connectivity}>
      <HomePlaceholder connectivity={connectivity} />
    </AppShell>
  );
}
