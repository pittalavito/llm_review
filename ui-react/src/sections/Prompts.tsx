/** Port of ui/js/sections/prompts.js — prompt version registry (CRUD). */
import { useCallback, useEffect, useState, type FormEvent } from 'react';
import {
  createPromptVersion,
  getPromptVersion,
  listPromptVersions,
  updatePromptVersion,
} from '../api/client';
import type { AgentRole, PromptVersion, PromptVersionMeta } from '../api/types';
import { errorMessage, formatTimestamp } from '../lib/format';

const ROLE_LABELS: Record<AgentRole, string> = {
  reviewer:      '👤 Reviewer (1–3)',
  meta_reviewer: '📋 Meta Reviewer',
  area_chair:    '🏛️ Area Chair',
  author_agent:  '✍️ Author Agent',
};
const ROLES = Object.keys(ROLE_LABELS) as AgentRole[];

export default function Prompts() {
  const [versions, setVersions] = useState<PromptVersionMeta[]>([]);
  const [roleFilter, setRoleFilter] = useState('');
  const [showInactive, setShowInactive] = useState(false);
  const [listError, setListError] = useState('');
  const [detail, setDetail] = useState<PromptVersion | null>(null);

  const refresh = useCallback(async () => {
    setListError('');
    try {
      setVersions(await listPromptVersions({
        agent_role: roleFilter || undefined,
        include_inactive: showInactive,
      }));
    } catch (err) {
      setVersions([]);
      setListError(`Errore caricamento: ${errorMessage(err)}`);
    }
  }, [roleFilter, showInactive]);

  useEffect(() => { refresh(); }, [refresh]);

  async function onView(id: number) {
    try {
      setDetail(await getPromptVersion(id));
    } catch (err) {
      setListError(errorMessage(err));
    }
  }

  async function onToggle(version: PromptVersionMeta) {
    try {
      await updatePromptVersion(version.id, { is_active: !version.is_active });
      await refresh();
    } catch (err) {
      setListError(errorMessage(err));
    }
  }

  return (
    <div className="section">
      <h2 className="section__title">Prompt Versions</h2>
      <p className="section__desc">
        Registro delle versioni dei prompt base (tabella <code>prompt_version</code>).
        Le versioni sono immutabili: un testo nuovo è una versione nuova.
      </p>

      <div className="gr-card">
        <div className="gr-card-header-row">
          <div className="gr-card-title">Versioni registrate</div>
          <div className="gr-card-actions">
            <select
              className="form-select"
              style={{ width: 'auto', fontSize: '0.8rem' }}
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value)}
            >
              <option value="">Tutti i ruoli</option>
              {ROLES.map((role) => <option key={role} value={role}>{ROLE_LABELS[role]}</option>)}
            </select>
            <label style={{ fontSize: '0.8rem', whiteSpace: 'nowrap' }}>
              <input
                type="checkbox"
                className="form-checkbox"
                checked={showInactive}
                onChange={(e) => setShowInactive(e.target.checked)}
              /> mostra disattivate
            </label>
          </div>
        </div>

        {versions.length === 0 && !listError && <p className="muted">Nessuna versione registrata.</p>}
        {versions.length > 0 && (
          <table className="gr-config-table">
            <thead>
              <tr>
                <th>ID</th><th>Ruolo</th><th>Versione</th><th>Descrizione</th>
                <th>Creata</th><th>Attiva</th><th></th>
              </tr>
            </thead>
            <tbody>
              {versions.map((v) => (
                <tr key={v.id} style={v.is_active ? undefined : { opacity: 0.55 }}>
                  <td>{v.id}</td>
                  <td>{ROLE_LABELS[v.agent_role] ?? v.agent_role}</td>
                  <td><code>{v.version_label}</code></td>
                  <td>{v.description ?? ''}</td>
                  <td><small>{formatTimestamp(v.created_at)}</small></td>
                  <td>{v.is_active ? '✅' : '🚫'}</td>
                  <td style={{ whiteSpace: 'nowrap' }}>
                    <button className="btn btn--ghost btn--sm" title="Mostra template"
                            onClick={() => onView(v.id)}>👁</button>
                    <button className="btn btn--ghost btn--sm"
                            title={v.is_active ? 'Disattiva' : 'Riattiva'}
                            onClick={() => onToggle(v)}>
                      {v.is_active ? 'Disattiva' : 'Riattiva'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {listError && <div className="error-msg">{listError}</div>}
      </div>

      {detail && (
        <div className="gr-card">
          <div className="gr-card-header-row">
            <div className="gr-card-title">
              Template — {detail.agent_role}/{detail.version_label}
            </div>
            <button className="btn btn--ghost btn--sm" onClick={() => setDetail(null)}>✕ Chiudi</button>
          </div>
          <p className="muted" style={{ fontSize: '0.8rem' }}>
            {detail.description ?? ''} · sha256 {detail.template_hash.slice(0, 12)}… ·
            creata {formatTimestamp(detail.created_at)}
          </p>
          <pre style={{
            whiteSpace: 'pre-wrap', fontSize: '0.85rem', lineHeight: 1.5,
            background: 'var(--c-bg, #f6f4ef)', padding: 'var(--s-3, 1rem)', borderRadius: 4,
          }}>
            {detail.template}
          </pre>
        </div>
      )}

      <CreateVersionCard onCreated={refresh} />
    </div>
  );
}

function CreateVersionCard({ onCreated }: { onCreated: () => Promise<void> }) {
  const [role, setRole] = useState<AgentRole>('reviewer');
  const [label, setLabel] = useState('');
  const [description, setDescription] = useState('');
  const [template, setTemplate] = useState('');
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError('');
    setStatus('');
    if (!label.trim()) { setError("Inserisci un'etichetta (es. v3)."); return; }
    if (!template.trim()) { setError('Inserisci il testo del template.'); return; }

    setBusy(true);
    try {
      await createPromptVersion({
        agent_role: role,
        version_label: label.trim(),
        template: template.trim(),
        ...(description.trim() ? { description: description.trim() } : {}),
      });
      setStatus(`✅ Creata ${role}/${label.trim()}`);
      setLabel('');
      setDescription('');
      setTemplate('');
      await onCreated();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="gr-card" onSubmit={onSubmit}>
      <div className="gr-card-title">Nuova versione</div>
      <div className="form-group form-group--inline">
        <label className="form-label">Ruolo</label>
        <select className="form-select" style={{ width: 'auto' }} value={role}
                onChange={(e) => setRole(e.target.value as AgentRole)}>
          {ROLES.map((r) => <option key={r} value={r}>{ROLE_LABELS[r]}</option>)}
        </select>
        <label className="form-label" style={{ marginLeft: 'var(--s-3, 1rem)' }}>Etichetta</label>
        <input className="form-input" style={{ width: '6rem' }} placeholder="v3" maxLength={50}
               value={label} onChange={(e) => setLabel(e.target.value)} />
      </div>
      <div className="form-group">
        <label className="form-label">Descrizione (opzionale)</label>
        <input className="form-input" maxLength={500}
               placeholder="Es. variante più severa sui claim teorici"
               value={description} onChange={(e) => setDescription(e.target.value)} />
      </div>
      <div className="form-group">
        <label className="form-label">Template</label>
        <textarea className="form-textarea" rows={7} placeholder="Testo del system prompt base…"
                  value={template} onChange={(e) => setTemplate(e.target.value)} />
      </div>
      <div className="gr-card-footer">
        <button className="btn btn--primary" type="submit" disabled={busy}>＋ Crea versione</button>
        <span className={`gr-status${status ? ' gr-status--ok' : ''}`}>
          {busy ? '⏳ Creazione…' : status}
        </span>
      </div>
      {error && <div className="error-msg">{error}</div>}
    </form>
  );
}
