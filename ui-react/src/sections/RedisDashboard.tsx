/** Embeds redis-commander, the web dashboard for the project's Redis cache.
 * Runs as a separate container (docker compose up -d, or
 * scripts/run-redis-dashboard.py) on host port 8082 — start it before opening
 * this section. Absolute URL because it's a different origin than the app. */

const DASHBOARD_URL = 'http://localhost:8083';

export default function RedisDashboard() {
  return (
    <div className="redis-dashboard-section">
      <h2 className="section-title">Redis</h2>
      <p className="section-description">
        Dashboard della cache Redis (redis-commander). Avviala con{' '}
        <code>docker compose up -d</code> o{' '}
        <code>uv run python scripts/run-redis-dashboard.py</code>.{' '}
        <a href={DASHBOARD_URL} target="_blank" rel="noreferrer">
          Apri in una nuova scheda ↗
        </a>
      </p>

      <div className="redis-dashboard-frame">
        <iframe
          src={DASHBOARD_URL}
          title="Redis Commander"
          className="redis-dashboard-frame__iframe"
        />
      </div>
    </div>
  );
}
