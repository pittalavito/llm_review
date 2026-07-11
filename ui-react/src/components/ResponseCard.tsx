/**
 * Response card with status badge, formatted body and optional raw-LLM-output
 * panel. Shared by Test Agent and Test RAG (same structure, different CSS
 * prefixes in the vanilla UI — kept via the prefix prop).
 */

export interface ResponseState {
  title: string;
  body: string;
  isError: boolean;
  rawOutput: string | null;
}

export default function ResponseCard({
  state,
  prefix,
}: {
  state: ResponseState | null;
  prefix: 'test-agent' | 'test-rag';
}) {
  if (!state) return null;
  return (
    <div className={
      `card ${prefix}-response${state.isError ? ` ${prefix}-response--error` : ''}`
    }>
      <div className="card__header">
        <span className={`badge badge--${state.isError ? 'error' : 'success'}`}>
          {state.isError ? 'Error' : 'Completed'}
        </span>
        <span className="card__title">{state.title}</span>
      </div>
      <div className={`card__body ${prefix}-response__body`}>
        <pre>{state.body}</pre>
        {state.rawOutput && (
          <details className={`${prefix}-raw-output`}>
            <summary className={`${prefix}-raw-output__summary`}>Raw LLM output</summary>
            <pre className={`${prefix}-raw-output__body`}>{state.rawOutput}</pre>
          </details>
        )}
      </div>
    </div>
  );
}
