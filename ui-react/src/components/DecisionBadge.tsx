/** Decision badge map — single source replacing the vanilla copies in
 * storico.js / compare.js / graphrun.js. */

export interface BadgeInfo {
  label: string;
  cls: string;
}

const DECISION_BADGE: Record<string, BadgeInfo> = {
  accept:         { label: 'ACCEPT',         cls: 'badge--accept' },
  minor_revision: { label: 'MINOR REVISION', cls: 'badge--minor' },
  major_revision: { label: 'MAJOR REVISION', cls: 'badge--major' },
  reject:         { label: 'REJECT',         cls: 'badge--reject' },
};

export function decisionInfo(decision: string | null | undefined): BadgeInfo {
  const key = (decision || 'unknown').toLowerCase().replace(/ /g, '_');
  return DECISION_BADGE[key] ?? { label: key.toUpperCase(), cls: 'badge--unknown' };
}

export default function DecisionBadge({
  decision,
  small = false,
}: {
  decision: string | null | undefined;
  small?: boolean;
}) {
  const badge = decisionInfo(decision);
  return (
    <span className={`badge${small ? ' badge--sm' : ''} ${badge.cls}`}>{badge.label}</span>
  );
}
