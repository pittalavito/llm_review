/**
 * Backup DB section — downloads the whole database as a ZIP built server-side
 * in memory. The browser's own save dialog picks the destination folder.
 */
import { useState } from 'react';
import { downloadBackup } from '../api/client';
import { errorMessage } from '../lib/format';

export default function Backup() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [lastFile, setLastFile] = useState('');

  async function onDownload() {
    setLoading(true);
    setError('');
    setLastFile('');
    try {
      const { blob, filename } = await downloadBackup();
      // Force a download via a temporary <a>; the browser dialog chooses where.
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      setLastFile(filename);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="section">
      <h2 className="section__title">Backup DB</h2>
      <p className="section__desc">
        Esporta tutto il contenuto del database in un archivio <code>.zip</code>: una
        sottocartella per tabella, con un CSV delle colonne indicizzate e un JSON per record
        delle colonne-payload, più un <code>manifest.json</code>. Il file viene scaricato dal
        browser — scegli tu dove salvarlo.
      </p>

      <div className="gr-card">
        <div className="gr-card-title">Scarica backup</div>
        <div className="gr-card-footer">
          <button className="btn btn--primary" onClick={onDownload} disabled={loading}>
            {loading ? '⏳ Preparazione…' : '⬇ Scarica backup DB'}
          </button>
          {lastFile && (
            <span className="gr-status gr-status--ok">✅ Scaricato: {lastFile}</span>
          )}
        </div>
        {error && <div className="error-msg">{error}</div>}
      </div>
    </div>
  );
}
