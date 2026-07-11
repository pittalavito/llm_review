/**
 * Plain-text formatter for agent responses shown in the Test Agent /
 * Test RAG response cards. The vanilla UI had two diverged copies
 * (testagent.js: reviewer fields; testrag.js: strengths/weaknesses);
 * here they are the two variants of one function, outputs unchanged.
 */

export type ResponseVariant = 'reviewer' | 'retrieval';

function asText(value: unknown): string {
  if (value == null) return '';
  if (typeof value === 'string') return value.trim();
  return String(value).trim();
}

function formatList(title: string, items: unknown): string {
  if (!Array.isArray(items) || items.length === 0) return '';
  const lines = [title];
  for (const item of items) {
    const content = asText(item);
    if (content) lines.push(`- ${content}`);
  }
  return lines.length > 1 ? lines.join('\n') : '';
}

export function formatAgentResponse(data: unknown, variant: ResponseVariant): string {
  if (!data || typeof data !== 'object') {
    return typeof data === 'string' ? data : JSON.stringify(data, null, 2);
  }

  const record = data as { agent?: unknown; payload?: unknown };
  const agent = asText(record.agent) || 'unknown_agent';
  const payload = record.payload;
  if (!payload || typeof payload !== 'object') {
    return `[${agent}]\n${JSON.stringify(payload, null, 2)}`;
  }

  const p = payload as Record<string, unknown>;
  const sections = [`[${agent}]`];
  const summary = asText(p.summary) || asText(p.analysis);
  if (summary) sections.push(`Summary\n${summary}`);

  if (variant === 'reviewer') {
    if (p.significance_and_novelty) {
      sections.push(`Significance & Novelty\n${asText(p.significance_and_novelty)}`);
    }
    const acceptance = formatList('Reasons for Acceptance', p.reasons_for_acceptance);
    if (acceptance) sections.push(acceptance);
    const rejection = formatList('Reasons for Rejection', p.reasons_for_rejection);
    if (rejection) sections.push(rejection);
    const suggestions = formatList('Suggestions', p.suggestions);
    if (suggestions) sections.push(suggestions);
    if (p.rating != null) sections.push(`Rating\n${p.rating}/10`);
    const confidence = asText(p.confidence);
    if (confidence) sections.push(`Confidence\n${confidence}/5`);
    if (p.recommendation) sections.push(`Recommendation\n${p.recommendation}`);
    if (p.decision) sections.push(`Decision\n${p.decision}`);
    if (p.justification) sections.push(`Justification\n${asText(p.justification)}`);
  } else {
    const strengths = formatList('Strengths', p.strengths);
    if (strengths) sections.push(strengths);
    const weaknesses = formatList('Weaknesses', p.weaknesses);
    if (weaknesses) sections.push(weaknesses);
    const recommendations = formatList('Recommendations', p.recommendations);
    if (recommendations) sections.push(recommendations);
    const confidence = asText(p.confidence);
    if (confidence) sections.push(`Confidence\n${confidence}`);
  }

  if (sections.length === 1) sections.push(JSON.stringify(payload, null, 2));
  return sections.join('\n\n');
}
