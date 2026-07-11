/** Port of ui/js/sections/health.js — backend ping. */
import { useState } from 'react';
import { checkHealth } from '../api/client';

type HealthState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'ok'; text: string }
  | { status: 'error'; text: string };

export default function Health() {
  const [state, setState] = useState<HealthState>({ status: 'idle' });
  const loading = state.status === 'loading';

  async function onCheck() {
    setState({ status: 'loading' });
    try {
      const data = await checkHealth();
      setState({ status: 'ok', text: JSON.stringify(data, null, 2) });
    } catch (err) {
      setState({ status: 'error', text: err instanceof Error ? err.message : String(err) });
    }
  }

  return (
    <div className="health-section">
      <h2 className="section-title">Health Check</h2>
      <p className="section-description">Verifica lo stato del servizio backend.</p>

      <button className="btn btn--primary" onClick={onCheck} disabled={loading}>
        <span>{loading ? '⏳' : '🔍'}</span> {loading ? 'Checking…' : 'Check Health'}
      </button>

      {(state.status === 'ok' || state.status === 'error') && (
        <div className="health-response">
          <div className="card">
            <div className="card__header">
              <span className={`badge badge--${state.status === 'ok' ? 'success' : 'error'}`}>
                {state.status === 'ok' ? '✅ OK' : '❌ Error'}
              </span>
              <span className="card__title">Response</span>
            </div>
            <pre className="card__body">{state.text}</pre>
          </div>
        </div>
      )}
    </div>
  );
}
