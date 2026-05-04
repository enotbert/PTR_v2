const apiBase = import.meta.env.VITE_API_BASE_URL ?? "";

export default function App() {
  return (
    <main>
      <h1>PTR frontend (Vite dev)</h1>
      <p data-testid="api-base">
        <strong>VITE_API_BASE_URL:</strong> {apiBase || "(empty)"}
      </p>
      <p className="hint">
        Configure in <code>.env.development</code> or <code>docker-compose.yml</code> (see{" "}
        <code>docs/tech/docker-dev.md</code>).
      </p>
    </main>
  );
}
