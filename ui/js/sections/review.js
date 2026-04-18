/**
 * sections/review.js — Future real-review area.
 */

export function render() {
  const el = document.createElement('section');
  el.className = 'review-section';
  el.innerHTML = `
    <h2 class="section-title">Review</h2>
    <p class="section-description">Area dedicata alla vera revisione. Qui verranno ospitate le nuove chiamate review non-dev.</p>

    <div class="card">
      <div class="card__header">
        <span class="card__title">Review Controller</span>
      </div>
      <div class="card__body">
        Endpoint review in preparazione. Questa sezione sara estesa con run della revisione reale.
      </div>
    </div>
  `;
  return el;
}

export function mount() {
  // Placeholder section: no interactions yet.
}
