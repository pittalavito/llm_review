/**
 * sections/openreview.js — OpenReview exploration and paper summary test section.
 */

import { getOpenReviewPaperSummary, searchOpenReviewPapers } from '../api.js';

function safeParseLimit(value) {
  const parsed = Number.parseInt(value, 10);
  if (!Number.isFinite(parsed)) return 10;
  if (parsed < 1) return 1;
  if (parsed > 100) return 100;
  return parsed;
}

export function render() {
  const el = document.createElement('section');
  el.className = 'open-review-section';
  el.innerHTML = `
    <h2 class="section-title">OpenReview Test Area</h2>
    <p class="section-description">Search papers by venue + keyword and inspect live paper summaries from backend endpoints.</p>

    <div class="open-review-grid">
      <div class="card open-review-panel">
        <div class="card__header">
          <span class="card__title">1) Search Papers</span>
        </div>
        <div class="card__body open-review-panel__body">
          <form id="open-review-search-form" class="open-review-form" novalidate>
            <label class="open-review-field">
              <span class="open-review-field__label">Keyword</span>
              <input class="open-review-field__control" id="open-review-keyword" type="text" maxlength="200" placeholder="e.g. llm, diffusion, benchmark" />
            </label>

            <label class="open-review-field">
              <span class="open-review-field__label">Venue ID</span>
              <input class="open-review-field__control" id="open-review-venue" type="text" maxlength="300" placeholder="e.g. ICLR.cc/2025/Conference" />
            </label>

            <label class="open-review-field">
              <span class="open-review-field__label">Limit</span>
              <input class="open-review-field__control" id="open-review-limit" type="number" min="1" max="100" value="10" />
            </label>

            <div class="open-review-actions">
              <button class="btn btn--primary" id="open-review-search-btn" type="submit">Search</button>
            </div>
          </form>

          <div class="open-review-result" id="open-review-search-result" hidden>
            <div class="open-review-result__head">
              <strong class="open-review-result__title">Search Results</strong>
              <span class="badge" id="open-review-search-badge"></span>
            </div>
            <div class="open-review-list" id="open-review-list"></div>
          </div>
        </div>
      </div>

      <div class="card open-review-panel">
        <div class="card__header">
          <span class="card__title">2) Get Paper Summary</span>
        </div>
        <div class="card__body open-review-panel__body">
          <form id="open-review-summary-form" class="open-review-form" novalidate>
            <label class="open-review-field">
              <span class="open-review-field__label">Paper ID</span>
              <input class="open-review-field__control" id="open-review-paper-id" type="text" maxlength="400" placeholder="Paste paper note ID or select from results" />
            </label>

            <div class="open-review-actions">
              <button class="btn btn--primary" id="open-review-summary-btn" type="submit">Get Summary</button>
            </div>
          </form>

          <div class="card open-review-json" id="open-review-summary-card" hidden>
            <div class="card__header">
              <span class="badge" id="open-review-summary-badge"></span>
              <span class="card__title" id="open-review-summary-title">Summary</span>
            </div>
            <pre class="card__body" id="open-review-summary-json"></pre>
          </div>
        </div>
      </div>
    </div>

    <div class="card open-review-trace" id="open-review-trace-card">
      <div class="card__header">
        <span class="card__title">What Happens Under the Hood</span>
      </div>
      <div class="card__body">
        <ol class="open-review-trace__list" id="open-review-trace-list">
          <li>Ready. Start with a search or request a summary.</li>
        </ol>
      </div>
    </div>
  `;
  return el;
}

export function mount(container) {
  const searchForm = container.querySelector('#open-review-search-form');
  const keywordInput = container.querySelector('#open-review-keyword');
  const venueInput = container.querySelector('#open-review-venue');
  const limitInput = container.querySelector('#open-review-limit');
  const searchButton = container.querySelector('#open-review-search-btn');
  const searchResult = container.querySelector('#open-review-search-result');
  const searchBadge = container.querySelector('#open-review-search-badge');
  const listEl = container.querySelector('#open-review-list');
  const summaryForm = container.querySelector('#open-review-summary-form');
  const paperIdInput = container.querySelector('#open-review-paper-id');
  const summaryButton = container.querySelector('#open-review-summary-btn');
  const summaryCard = container.querySelector('#open-review-summary-card');
  const summaryBadge = container.querySelector('#open-review-summary-badge');
  const summaryTitle = container.querySelector('#open-review-summary-title');
  const summaryJson = container.querySelector('#open-review-summary-json');
  const traceList = container.querySelector('#open-review-trace-list');

  function addTrace(text) {
    const item = document.createElement('li');
    item.textContent = text;
    traceList.appendChild(item);
    while (traceList.children.length > 10) {
      traceList.removeChild(traceList.firstElementChild);
    }
  }

  function setSearchLoading(loading) {
    searchButton.disabled = loading;
    keywordInput.disabled = loading;
    venueInput.disabled = loading;
    limitInput.disabled = loading;
    searchButton.textContent = loading ? 'Searching…' : 'Search';
  }

  function setSummaryLoading(loading) {
    summaryButton.disabled = loading;
    paperIdInput.disabled = loading;
    summaryButton.textContent = loading ? 'Loading…' : 'Get Summary';
  }

  function renderSearchResults(results) {
    listEl.innerHTML = '';

    if (results.length === 0) {
      const empty = document.createElement('p');
      empty.className = 'open-review-empty';
      empty.textContent = 'No papers found for this query.';
      listEl.appendChild(empty);
      return;
    }

    for (const item of results) {
      const card = document.createElement('article');
      card.className = 'open-review-item';
      card.innerHTML = `
        <h3 class="open-review-item__title">${item.title || '(Untitled)'}</h3>
        <p class="open-review-item__meta"><strong>ID:</strong> ${item.id}</p>
        <p class="open-review-item__meta"><strong>Venue:</strong> ${item.venue || '(n/a)'}</p>
        <p class="open-review-item__abstract">${item.abstract || '(No abstract)'}</p>
        <div class="open-review-item__actions">
          <button class="btn btn--primary open-review-item__button" data-paper-id="${item.id}" type="button">Use This ID</button>
        </div>
      `;

      const useButton = card.querySelector('button[data-paper-id]');
      useButton.addEventListener('click', () => {
        paperIdInput.value = item.id;
        paperIdInput.focus();
        addTrace(`Paper ID selected from search results: ${item.id}`);
      });

      listEl.appendChild(card);
    }
  }

  function showSummary(title, payload, isError = false) {
    summaryTitle.textContent = title;
    summaryJson.textContent = typeof payload === 'string' ? payload : JSON.stringify(payload, null, 2);
    summaryBadge.textContent = isError ? 'Error' : 'OK';
    summaryBadge.className = isError ? 'badge badge--error' : 'badge badge--success';
    summaryCard.hidden = false;
  }

  searchForm.addEventListener('submit', async (event) => {
    event.preventDefault();

    const keyword = keywordInput.value.trim();
    const venueId = venueInput.value.trim();
    const limit = safeParseLimit(limitInput.value);

    if (!keyword || !venueId) {
      addTrace('Search blocked: keyword and venue_id are required.');
      searchBadge.textContent = 'Validation error';
      searchBadge.className = 'badge badge--error';
      searchResult.hidden = false;
      listEl.innerHTML = '<p class="open-review-empty">Insert both keyword and venue ID.</p>';
      return;
    }

    setSearchLoading(true);
    searchResult.hidden = true;
    addTrace(`Sending POST /openreview/papers/search with keyword='${keyword}', venue_id='${venueId}', limit=${limit}.`);

    try {
      const results = await searchOpenReviewPapers({
        keyword,
        venue_id: venueId,
        limit,
      });

      addTrace(`Search completed. Backend returned ${results.length} paper(s).`);
      searchBadge.textContent = `${results.length} result(s)`;
      searchBadge.className = 'badge badge--success';
      renderSearchResults(results);
      searchResult.hidden = false;
    } catch (err) {
      addTrace(`Search failed: ${err.message}`);
      searchBadge.textContent = 'Search failed';
      searchBadge.className = 'badge badge--error';
      listEl.innerHTML = `<p class="open-review-empty">Error: ${err.message}</p>`;
      searchResult.hidden = false;
    } finally {
      setSearchLoading(false);
    }
  });

  summaryForm.addEventListener('submit', async (event) => {
    event.preventDefault();

    const paperId = paperIdInput.value.trim();
    if (!paperId) {
      addTrace('Summary blocked: paper ID is required.');
      showSummary('Validation error', 'Insert a paper ID before requesting summary.', true);
      return;
    }

    setSummaryLoading(true);
    summaryCard.hidden = true;
    addTrace(`Sending GET /openreview/papers/${paperId}/summary.`);

    try {
      const summary = await getOpenReviewPaperSummary(paperId);
      addTrace('Summary loaded: submission + reviews + decision aggregated by backend.');
      showSummary(`Summary for ${paperId}`, summary, false);
    } catch (err) {
      addTrace(`Summary failed: ${err.message}`);
      showSummary('Summary request failed', err.message, true);
    } finally {
      setSummaryLoading(false);
    }
  });

  keywordInput.focus();
}
