/** Port of ui/js/sections/compare.js — human vs LLM review comparison. */
import { useEffect, useState, type ReactNode } from 'react';
import { comparePaper, listComparablePapers } from '../api/client';
import type {
  ComparablePaper,
  HumanMetaReview,
  HumanReview,
  LLMAreaChair,
  LLMMetaReview,
  LLMReview,
  PaperComparison,
  PaperComparisonResult,
} from '../api/types';
import DecisionBadge, { decisionInfo } from '../components/DecisionBadge';
import { errorMessage } from '../lib/format';

export default function Compare() {
  const [papers, setPapers] = useState<ComparablePaper[]>([]);
  const [paper, setPaper] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<PaperComparison | null>(null);
  const [listReady, setListReady] = useState(false);

  useEffect(() => {
    let alive = true;
    listComparablePapers()
      .then((items) => { if (alive) { setPapers(items); setListReady(true); } })
      .catch((err) => { if (alive) setError(`Errore nel caricare i paper: ${errorMessage(err)}`); });
    return () => { alive = false; };
  }, []);

  async function onCompare() {
    if (!paper) return;
    setError('');
    setLoading(true);
    setData(null);
    try {
      setData(await comparePaper(paper));
    } catch (err) {
      setError(`Errore: ${errorMessage(err)}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="section comparison">
      <h2 className="section__title">Confronto Review</h2>
      <p className="section__desc">
        Seleziona un paper dall'indice OpenReview per confrontare le review umane con quelle
        generate dal sistema.
      </p>
      {error && <div className="error-msg">{error}</div>}
      <div className="cmp-controls">
        <div className="form-group">
          <label className="form-label" htmlFor="cmp-paper-select">Paper</label>
          <select id="cmp-paper-select" className="form-select" value={paper}
                  onChange={(e) => setPaper(e.target.value)}>
            <option value="">{listReady ? '-- Seleziona paper --' : '-- Caricamento… --'}</option>
            {papers.map((p) => (
              <option key={p.paper_path} value={p.paper_path}>[{p.conference}] {p.title}</option>
            ))}
          </select>
        </div>
        <button className="btn btn--primary" disabled={!listReady || loading} onClick={onCompare}>
          Confronta
        </button>
      </div>

      {loading && <p className="cmp-loading">Caricamento dati OpenReview e confronto in corso…</p>}
      {data && <ComparisonResult data={data} />}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Result
// ---------------------------------------------------------------------------

function ComparisonResult({ data }: { data: PaperComparison }) {
  const runs = data.run_comparisons ?? [];
  const humanMeta = runs.find((rc) => rc.human_meta_review)?.human_meta_review ?? null;

  return (
    <div>
      <div className="cmp-paper-header">
        <div className="cmp-paper-title">{data.title}</div>
        <div className="cmp-paper-meta">
          <span>{data.conference}</span>
          <span>Forum: <code>{data.forum_id}</code></span>
          <span>Decisione umana: <DecisionBadge decision={data.human_decision} /></span>
          <span>{data.human_reviews.length} reviewer umani</span>
        </div>
      </div>

      {runs.length === 0 && <p className="muted">Nessun run trovato per questo paper.</p>}
      {runs.length > 0 && (
        <>
          <div className="cmp-section-label">Run analizzati</div>
          {runs.map((rc) => <RunSummaryStrip key={rc.run_id} rc={rc} />)}
        </>
      )}

      <div className="cmp-section-label">Review (umane e LLM, elencate)</div>
      <ReviewTable humanReviews={data.human_reviews} runs={runs} />

      <MetaTable humanMeta={humanMeta} runs={runs} />
    </div>
  );
}

function RunSummaryStrip({ rc }: { rc: PaperComparisonResult }) {
  const badge = decisionInfo(rc.llm_decision || '');
  return (
    <div className="cmp-run-summary">
      <span><strong>Run:</strong> {rc.run_description || rc.run_id}</span>
      <span>
        <strong>LLM:</strong>{' '}
        <span className={`badge badge--sm ${badge.cls}`}>{badge.label}</span>
      </span>
      {rc.decision_match
        ? <span className="cmp-match-yes">✓ concordante</span>
        : <span className="cmp-match-no">✗ discordante</span>}
      <span className="muted">{rc.human_review_count} umane · {rc.llm_review_count} LLM</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Expandable paired rows
// ---------------------------------------------------------------------------

interface RowCell {
  content: ReactNode;
  className?: string;
}

function ExpandableRow({
  kind, cells, detail, columns,
}: {
  kind: 'human' | 'llm';
  cells: RowCell[];
  detail: ReactNode;
  columns: number;
}) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <tr className={`cmp-row cmp-row--${kind}${open ? ' is-open' : ''}`}
          onClick={() => setOpen(!open)}>
        <td className="cmp-toggle-cell"><span className="cmp-toggle">▸</span></td>
        <td>
          <span className={`cmp-tag cmp-tag--${kind}`}>{kind === 'human' ? 'Umano' : 'LLM'}</span>
        </td>
        {cells.map((cell, i) => <td key={i} className={cell.className}>{cell.content}</td>)}
      </tr>
      <tr className="cmp-detail" hidden={!open}>
        <td colSpan={columns}>{detail}</td>
      </tr>
    </>
  );
}

function Field({ label, value }: { label: string; value: string | null | undefined }) {
  if (!value) return null;
  return (
    <>
      <div className="cmp-field-label">{label}</div>
      <div className="cmp-text">{value}</div>
    </>
  );
}

function FieldList({ label, items }: { label: string; items: string[] }) {
  if (!items.length) return null;
  return (
    <>
      <div className="cmp-field-label">{label}</div>
      <ul className="cmp-list">{items.map((s, i) => <li key={i}>{s}</li>)}</ul>
    </>
  );
}

// ---------------------------------------------------------------------------
// Review table
// ---------------------------------------------------------------------------

function ReviewTable({ humanReviews, runs }: { humanReviews: HumanReview[]; runs: PaperComparisonResult[] }) {
  const llmRows = runs.flatMap((rc) =>
    (rc.llm_reviews ?? []).map((review) => ({ review, runLabel: rc.run_description || rc.run_id })),
  );
  if (!humanReviews.length && !llmRows.length) {
    return <p className="cmp-missing">Nessuna review disponibile.</p>;
  }
  return (
    <table className="cmp-table">
      <thead>
        <tr>
          <th className="cmp-th-toggle"></th>
          <th>Tipo</th>
          <th>Run</th>
          <th>Reviewer</th>
          <th className="cmp-num">Rating</th>
          <th className="cmp-num">Confidence</th>
        </tr>
      </thead>
      <tbody>
        {humanReviews.map((h) => <HumanReviewRow key={h.note_id} review={h} />)}
        {llmRows.map(({ review, runLabel }, i) => (
          <LlmReviewRow key={`${runLabel}-${review.agent}-${i}`} review={review} runLabel={runLabel} />
        ))}
      </tbody>
    </table>
  );
}

function HumanReviewRow({ review }: { review: HumanReview }) {
  return (
    <ExpandableRow
      kind="human"
      columns={6}
      cells={[
        { content: '—', className: 'muted' },
        { content: review.reviewer_id || '?' },
        { content: review.rating != null ? `${review.rating}/10` : '—', className: 'cmp-num' },
        { content: review.confidence != null ? `${review.confidence}/5` : '—', className: 'cmp-num' },
      ]}
      detail={
        <>
          <Field label="Valutazione" value={review.rating_label} />
          <Field label="Sommario paper" value={review.summary} />
          <Field label="Punti di forza" value={review.strengths} />
          <Field label="Debolezze" value={review.weaknesses} />
          <Field label="Revisione completa" value={review.full_text} />
          <Field label="Domande / Note" value={review.questions} />
        </>
      }
    />
  );
}

function LlmReviewRow({ review, runLabel }: { review: LLMReview; runLabel: string }) {
  return (
    <ExpandableRow
      kind="llm"
      columns={6}
      cells={[
        { content: runLabel || '—', className: 'muted' },
        { content: review.agent || '?' },
        { content: review.rating != null ? `${review.rating}/10` : '—', className: 'cmp-num' },
        { content: review.confidence != null ? `${review.confidence}/5` : '—', className: 'cmp-num' },
      ]}
      detail={
        <>
          <Field label="Sommario" value={review.summary} />
          <Field label="Significato e novità" value={review.significance_and_novelty} />
          <FieldList label="Motivi accettazione" items={review.reasons_for_acceptance ?? []} />
          <FieldList label="Motivi rifiuto" items={review.reasons_for_rejection ?? []} />
          <FieldList label="Suggerimenti" items={review.suggestions ?? []} />
        </>
      }
    />
  );
}

// ---------------------------------------------------------------------------
// Meta table
// ---------------------------------------------------------------------------

function MetaTable({ humanMeta, runs }: { humanMeta: HumanMetaReview | null; runs: PaperComparisonResult[] }) {
  const llmRows = runs.flatMap((rc) => {
    const runLabel = rc.run_description || rc.run_id;
    const rows: { kind: 'meta' | 'ac'; meta?: LLMMetaReview; ac?: LLMAreaChair; runLabel: string }[] = [];
    if (rc.llm_meta_review) rows.push({ kind: 'meta', meta: rc.llm_meta_review, runLabel });
    if (rc.llm_area_chair) rows.push({ kind: 'ac', ac: rc.llm_area_chair, runLabel });
    return rows;
  });
  if (!humanMeta && !llmRows.length) return null;

  return (
    <>
      <div className="cmp-section-label">Meta Review (elencata)</div>
      <table className="cmp-table">
        <thead>
          <tr>
            <th className="cmp-th-toggle"></th>
            <th>Tipo</th>
            <th>Run</th>
            <th>Ruolo</th>
            <th>Valutazione</th>
          </tr>
        </thead>
        <tbody>
          {humanMeta && (
            <ExpandableRow
              kind="human"
              columns={5}
              cells={[
                { content: '—', className: 'muted' },
                { content: 'Area Chair' },
                { content: humanMeta.recommendation || '—' },
              ]}
              detail={
                <>
                  <Field label="Testo" value={humanMeta.text} />
                  <Field label="Raccomandazione" value={humanMeta.recommendation} />
                </>
              }
            />
          )}
          {llmRows.map((row, i) => row.kind === 'meta' ? (
            <ExpandableRow
              key={`meta-${i}`}
              kind="llm"
              columns={5}
              cells={[
                { content: row.runLabel, className: 'muted' },
                { content: 'Meta Reviewer' },
                { content: row.meta!.overall_score != null ? `${row.meta!.overall_score}/10` : '—' },
              ]}
              detail={
                <>
                  <Field label="Sommario" value={row.meta!.summary} />
                  <FieldList label="Punti chiave" items={row.meta!.key_points ?? []} />
                  <Field label="Raccomandazione" value={row.meta!.recommendation} />
                </>
              }
            />
          ) : (
            <ExpandableRow
              key={`ac-${i}`}
              kind="llm"
              columns={5}
              cells={[
                { content: row.runLabel, className: 'muted' },
                { content: 'Area Chair' },
                { content: row.ac!.decision ? <DecisionBadge decision={row.ac!.decision} small /> : '—' },
              ]}
              detail={
                <>
                  {row.ac!.confidence != null && (
                    <>
                      <div className="cmp-field-label">Confidence</div>
                      <div className="cmp-text">{row.ac!.confidence}/5</div>
                    </>
                  )}
                  <Field label="Sommario" value={row.ac!.summary} />
                  <Field label="Motivazione" value={row.ac!.justification} />
                </>
              }
            />
          ))}
        </tbody>
      </table>
    </>
  );
}
