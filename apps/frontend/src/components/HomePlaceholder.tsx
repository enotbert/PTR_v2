import { useGameplayActionGate } from "../hooks/useGameplayActionGate";
import type { ConnectivityState } from "../hooks/useNetworkAndApiStatus";

type Props = {
  connectivity: ConnectivityState;
};

export function HomePlaceholder({ connectivity }: Props) {
  const gameplayGate = useGameplayActionGate(connectivity);

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
          disabled={gameplayGate.blocked}
          aria-disabled={gameplayGate.blocked}
          onClick={() => {
            gameplayGate.runIfAllowed(() => {
              // Placeholder: real gameplay command will be wired in PTR combat/tavern flows.
            });
          }}
        >
          Start first raid
        </button>
        {gameplayGate.blocked && (
          <p className="home-placeholder__hint">{gameplayGate.message}</p>
        )}
      </div>
    </section>
  );
}
