import type { ConnectivityState } from "../hooks/useNetworkAndApiStatus";

type Props = {
  connectivity: ConnectivityState;
};

export function HomePlaceholder({ connectivity }: Props) {
  const canStart = connectivity === "ready";

  return (
    <section className="home-placeholder" aria-labelledby="home-title">
      <h1 id="home-title" className="home-placeholder__title">
        Pocket Raid Tavern
      </h1>
      <p className="home-placeholder__lede">
        Short sessions, shared tavern progress — tap in when you are online and
        the server is ready.
      </p>
      <div className="home-placeholder__cta">
        <button
          type="button"
          className="btn btn--primary"
          data-testid="primary-cta"
          disabled={!canStart}
          aria-disabled={!canStart}
        >
          Start first raid
        </button>
        {!canStart && (
          <p className="home-placeholder__hint">
            {connectivity === "checking"
              ? "Checking network and server…"
              : "Available when you are online and the server responds."}
          </p>
        )}
      </div>
    </section>
  );
}
