/**
 * sections/prompts.js — Prompt version registry.
 * Lists the versions stored in the DB, shows template texts, creates new
 * immutable versions and toggles is_active. Template text is never edited:
 * a new text means a new version (audit run -> exact prompt).
 */

import {
  listPromptVersions,
  getPromptVersion,
  createPromptVersion,
  updatePromptVersion,
} from '../api.js';

const ROLE_LABELS = {
  reviewer:      '👤 Reviewer (1–3)',
  meta_reviewer: '📋 Meta Reviewer',
  area_chair:    '🏛️ Area Chair',
  author_agent:  '✍️ Author Agent',
};
const ROLES = Object.keys(ROLE_LABELS);

// ---------------------------------------------------------------------------
// render
// ---------------------------------------------------------------------------

export function render() {
  const el = document.createElement('div');
  el.className = 'section';
  el.innerHTML = `
    <h2 class="section__title">Prompt Versions</h2>
    <p class="section__desc">
      Registro delle versioni dei prompt base (tabella <code>prompt_version</code>).
      Le versioni sono immutabili: un testo nuovo è una versione nuova.
    </p>

    <!-- Registro -->
    <div class="gr-card">
      <div class="gr-card-header-row">
        <div class="gr-card-title">Versioni registrate</div>
        <div class="gr-card-actions">
          <select id="pv-role-filter" class="form-select" style="width:auto;font-size:0.8rem">
            <option value="">Tutti i ruoli</option>
            ${ROLES.map(r => `<option value="${r}">${ROLE_LABELS[r]}</option>`).join('')}
          </select>
          <label style="font-size:0.8rem;white-space:nowrap">
            <input id="pv-show-inactive" type="checkbox" class="form-checkbox" /> mostra disattivate
          </label>
        </div>
      </div>
      <div id="pv-list"><p class="muted">Caricamento…</p></div>
      <div id="pv-list-error" class="error-msg" hidden></div>
    </div>

    <!-- Dettaglio template -->
    <div class="gr-card" id="pv-detail-card" hidden>
      <div class="gr-card-header-row">
        <div class="gr-card-title" id="pv-detail-title">Template</div>
        <button id="pv-detail-close" class="btn btn--ghost btn--sm">✕ Chiudi</button>
      </div>
      <p class="muted" id="pv-detail-meta" style="font-size:0.8rem"></p>
      <pre id="pv-detail-template"
           style="white-space:pre-wrap;font-size:0.85rem;line-height:1.5;background:var(--c-bg, #f6f4ef);padding:var(--s-3, 1rem);border-radius:4px"></pre>
    </div>

    <!-- Nuova versione -->
    <div class="gr-card">
      <div class="gr-card-title">Nuova versione</div>
      <div class="form-group form-group--inline">
        <label class="form-label">Ruolo</label>
        <select id="pv-new-role" class="form-select" style="width:auto">
          ${ROLES.map(r => `<option value="${r}">${ROLE_LABELS[r]}</option>`).join('')}
        </select>
        <label class="form-label" style="margin-left:var(--s-3, 1rem)">Etichetta</label>
        <input id="pv-new-label" class="form-input" style="width:6rem" placeholder="v3" maxlength="50" />
      </div>
      <div class="form-group">
        <label class="form-label">Descrizione (opzionale)</label>
        <input id="pv-new-description" class="form-input" maxlength="500"
               placeholder="Es. variante più severa sui claim teorici" />
      </div>
      <div class="form-group">
        <label class="form-label">Template</label>
        <textarea id="pv-new-template" class="form-textarea" rows="7"
                  placeholder="Testo del system prompt base…"></textarea>
      </div>
      <div class="gr-card-footer">
        <button id="pv-create-btn" class="btn btn--primary">＋ Crea versione</button>
        <span id="pv-create-status" class="gr-status"></span>
      </div>
      <div id="pv-create-error" class="error-msg" hidden></div>
    </div>
  `;
  return el;
}

// ---------------------------------------------------------------------------
// mount
// ---------------------------------------------------------------------------

export async function mount(el) {
  const listBody     = el.querySelector('#pv-list');
  const listError    = el.querySelector('#pv-list-error');
  const roleFilter   = el.querySelector('#pv-role-filter');
  const showInactive = el.querySelector('#pv-show-inactive');
  const detailCard   = el.querySelector('#pv-detail-card');
  const createBtn    = el.querySelector('#pv-create-btn');
  const createStatus = el.querySelector('#pv-create-status');
  const createError  = el.querySelector('#pv-create-error');

  async function refreshList() {
    hideError(listError);
    try {
      const versions = await listPromptVersions({
        agent_role: roleFilter.value || undefined,
        include_inactive: showInactive.checked,
      });
      renderList(listBody, versions);
    } catch (e) {
      listBody.innerHTML = '';
      showError(listError, `Errore caricamento: ${e.message}`);
    }
  }

  // List interactions (event delegation on the table body)
  listBody.addEventListener('click', async (ev) => {
    const viewBtn   = ev.target.closest('[data-view-id]');
    const toggleBtn = ev.target.closest('[data-toggle-id]');

    if (viewBtn) {
      try {
        const version = await getPromptVersion(Number(viewBtn.dataset.viewId));
        showDetail(el, version);
      } catch (e) {
        showError(listError, e.message);
      }
    }

    if (toggleBtn) {
      toggleBtn.disabled = true;
      try {
        await updatePromptVersion(Number(toggleBtn.dataset.toggleId), {
          is_active: toggleBtn.dataset.active !== 'true',
        });
        await refreshList();
      } catch (e) {
        showError(listError, e.message);
        toggleBtn.disabled = false;
      }
    }
  });

  el.querySelector('#pv-detail-close').addEventListener('click', () => {
    detailCard.hidden = true;
  });

  roleFilter.addEventListener('change', refreshList);
  showInactive.addEventListener('change', refreshList);

  // Create
  createBtn.addEventListener('click', async () => {
    hideError(createError);
    createStatus.textContent = '';

    const payload = {
      agent_role:    el.querySelector('#pv-new-role').value,
      version_label: el.querySelector('#pv-new-label').value.trim(),
      template:      el.querySelector('#pv-new-template').value.trim(),
    };
    const description = el.querySelector('#pv-new-description').value.trim();
    if (description) payload.description = description;

    if (!payload.version_label) { showError(createError, 'Inserisci un\'etichetta (es. v3).'); return; }
    if (!payload.template)      { showError(createError, 'Inserisci il testo del template.');   return; }

    createBtn.disabled = true;
    createStatus.textContent = '⏳ Creazione…';
    createStatus.className = 'gr-status';
    try {
      await createPromptVersion(payload);
      createStatus.textContent = `✅ Creata ${payload.agent_role}/${payload.version_label}`;
      createStatus.className = 'gr-status gr-status--ok';
      el.querySelector('#pv-new-label').value = '';
      el.querySelector('#pv-new-description').value = '';
      el.querySelector('#pv-new-template').value = '';
      await refreshList();
    } catch (e) {
      createStatus.textContent = '';
      showError(createError, e.message);
    } finally {
      createBtn.disabled = false;
    }
  });

  await refreshList();
}

// ---------------------------------------------------------------------------
// Rendering helpers
// ---------------------------------------------------------------------------

function renderList(container, versions) {
  if (!versions.length) {
    container.innerHTML = '<p class="muted">Nessuna versione registrata.</p>';
    return;
  }
  const rows = versions.map(v => `
    <tr${v.is_active ? '' : ' style="opacity:0.55"'}>
      <td>${v.id}</td>
      <td>${ROLE_LABELS[v.agent_role] || esc(v.agent_role)}</td>
      <td><code>${esc(v.version_label)}</code></td>
      <td>${esc(v.description || '')}</td>
      <td><small>${formatDate(v.created_at)}</small></td>
      <td>${v.is_active ? '✅' : '🚫'}</td>
      <td style="white-space:nowrap">
        <button class="btn btn--ghost btn--sm" data-view-id="${v.id}" title="Mostra template">👁</button>
        <button class="btn btn--ghost btn--sm" data-toggle-id="${v.id}" data-active="${v.is_active}"
                title="${v.is_active ? 'Disattiva' : 'Riattiva'}">${v.is_active ? 'Disattiva' : 'Riattiva'}</button>
      </td>
    </tr>
  `).join('');
  container.innerHTML = `
    <table class="gr-config-table">
      <thead>
        <tr><th>ID</th><th>Ruolo</th><th>Versione</th><th>Descrizione</th><th>Creata</th><th>Attiva</th><th></th></tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function showDetail(el, version) {
  const card = el.querySelector('#pv-detail-card');
  el.querySelector('#pv-detail-title').textContent =
    `Template — ${version.agent_role}/${version.version_label}`;
  el.querySelector('#pv-detail-meta').textContent =
    `${version.description || ''}  ·  sha256 ${String(version.template_hash).slice(0, 12)}…  ·  creata ${formatDate(version.created_at)}`;
  el.querySelector('#pv-detail-template').textContent = version.template;
  card.hidden = false;
  card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function formatDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString('it-IT', { dateStyle: 'short', timeStyle: 'short' });
}

function esc(value) {
  const div = document.createElement('div');
  div.textContent = String(value);
  return div.innerHTML;
}

function showError(el, msg) { el.textContent = msg; el.hidden = false; }
function hideError(el)      { el.hidden = true; }
