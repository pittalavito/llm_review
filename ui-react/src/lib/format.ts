/** Shared formatting utilities (vanilla parity). */

export function formatTimestamp(iso: string | null | undefined): string {
  if (!iso) return '';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString('it-IT', { dateStyle: 'short', timeStyle: 'short' });
}

export function errorMessage(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}
