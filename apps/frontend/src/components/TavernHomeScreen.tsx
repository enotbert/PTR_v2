import type { ConnectivityState } from "../hooks/useNetworkAndApiStatus";
import { useTavernHomeState } from "../hooks/useTavernHomeState";

type Props = {
  connectivity: ConnectivityState;
};

function formatTime(value: string | null | undefined): string {
  if (!value) {
    return "No recent contributions yet";
  }
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) {
    return "Recently";
  }
  return dt.toLocaleString();
}

function formatSource(source: string | null | undefined): string {
  if (!source) {
    return "Not available";
  }
  return source.replaceAll("_", " ");
}

export function TavernHomeScreen({ connectivity }: Props) {
  const home = useTavernHomeState(connectivity);

  if (home.status === "blocked") {
    return (
      <section className="tavern-home" aria-labelledby="tavern-home-title">
        <h1 id="tavern-home-title" className="tavern-home__title">
          Pocket Raid Tavern
        </h1>
        <p className="tavern-home__status" data-testid="tavern-blocked">
          {home.message}
        </p>
        <button
          type="button"
          className="btn btn--primary"
          data-testid="primary-cta"
          disabled
          aria-disabled="true"
        >
          Start first raid
        </button>
      </section>
    );
  }

  if (home.status === "loading") {
    return (
      <section className="tavern-home" aria-labelledby="tavern-home-title">
        <h1 id="tavern-home-title" className="tavern-home__title">
          Pocket Raid Tavern
        </h1>
        <p className="tavern-home__status" data-testid="tavern-loading">
          {home.message}
        </p>
      </section>
    );
  }

  if (home.status === "error") {
    return (
      <section className="tavern-home" aria-labelledby="tavern-home-title">
        <h1 id="tavern-home-title" className="tavern-home__title">
          Pocket Raid Tavern
        </h1>
        <p className="tavern-home__status" data-testid="tavern-error">
          {home.message}
        </p>
        <button
          type="button"
          className="btn btn--primary"
          data-testid="primary-cta"
          disabled
          aria-disabled="true"
        >
          Start first raid
        </button>
      </section>
    );
  }

  const { data } = home;
  const percent =
    data.current_project.target_points > 0
      ? Math.min(
          100,
          Math.round(
            (data.current_project.progress_points /
              data.current_project.target_points) *
              100,
          ),
        )
      : 0;

  return (
    <section className="tavern-home" aria-labelledby="tavern-home-title">
      <h1 id="tavern-home-title" className="tavern-home__title">
        Pocket Raid Tavern
      </h1>
      <p className="tavern-home__lede">
        Gather your party for quick raids and keep the tavern project moving.
      </p>

      <button
        type="button"
        className="btn btn--primary"
        data-testid="primary-cta"
      >
        Start first raid
      </button>

      <article className="tavern-card" data-testid="tavern-project">
        <h2 className="tavern-card__title">Current project</h2>
        <p className="tavern-card__strong">{data.current_project.title}</p>
        <p className="tavern-card__meta">
          {data.current_project.progress_points} /{" "}
          {data.current_project.target_points} points
        </p>
        <div
          className="tavern-progress"
          role="progressbar"
          aria-label="Project progress"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={percent}
        >
          <div
            className="tavern-progress__fill"
            style={{ width: `${percent}%` }}
          />
        </div>
      </article>

      <article className="tavern-card" data-testid="tavern-contribution">
        <h2 className="tavern-card__title">Rewards and contribution</h2>
        <p className="tavern-card__meta">Weekly points: {data.weekly_points}</p>
        <p className="tavern-card__meta">Reputation: {data.reputation}</p>
        <p className="tavern-card__meta">
          Latest contribution: {data.contribution_summary.latest_amount ?? 0} (
          {formatSource(data.contribution_summary.latest_source_type)})
        </p>
        <p className="tavern-card__meta">
          Updated: {formatTime(data.contribution_summary.latest_at ?? null)}
        </p>
      </article>

      <article className="tavern-card" data-testid="tavern-chronicle">
        <h2 className="tavern-card__title">Chronicle</h2>
        {data.chronicle && data.chronicle.length > 0 ? (
          <ul className="tavern-chronicle">
            {data.chronicle.map((entry) => (
              <li className="tavern-chronicle__item" key={entry.id}>
                +{entry.amount} from {formatSource(entry.source_type)}
              </li>
            ))}
          </ul>
        ) : (
          <p className="tavern-card__meta">
            No events yet. Complete your first raid.
          </p>
        )}
      </article>
    </section>
  );
}
