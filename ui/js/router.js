/**
 * router.js — client-side section registry and navigation.
 *
 * Struttura minimale: solo le sezioni necessarie agli endpoint /health, /models, /test-llm.
 */

/** @type {Map<string, { render: () => HTMLElement, mount: (el: HTMLElement) => void }>} */
const _registry = new Map();

/**
 * Register a section.
 * @param {string} id
 * @param {{ render: () => HTMLElement, mount: (el: HTMLElement) => void }} section
 */
export function registerSection(id, section) {
  _registry.set(id, section);
}

/**
 * Swap the content area to the given section and update sidebar active state.
 * @param {string} id
 */
export function navigate(id) {
  const section = _registry.get(id);
  if (!section) return;

  // Update sidebar active indicator
  document.querySelectorAll('.nav__item').forEach(el => {
    el.classList.toggle('nav__item--active', el.dataset.section === id);
  });

  // Replace content area
  const contentArea = document.getElementById('content-area');
  contentArea.innerHTML = '';
  const el = section.render();
  contentArea.appendChild(el);
  section.mount(el);
}

/** Attach click listeners to all sidebar nav items. */
export function initRouter() {
  document.querySelectorAll('.nav__item').forEach(el => {
    el.addEventListener('click', () => navigate(el.dataset.section));
  });
}
