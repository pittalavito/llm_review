/** Embeds FastAPI's built-in Swagger UI (/docs) so the API can be explored
 * without leaving the React app. Same-origin in deployed mode; proxied to the
 * backend (8081) in dev via vite.config.ts. */

export default function Swagger() {
  return (
    <div className="swagger-section">
      <h2 className="section-title">API Docs</h2>
      <p className="section-description">
        Documentazione interattiva OpenAPI del backend.{' '}
        <a href="/docs" target="_blank" rel="noreferrer">
          Apri in una nuova scheda ↗
        </a>
      </p>

      <div className="swagger-frame">
        <iframe src="/docs" title="API Docs" className="swagger-frame__iframe" />
      </div>
    </div>
  );
}
