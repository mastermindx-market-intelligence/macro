/** Pure presentation helpers for the synthetic review fixture; no production imports. */
export function escapeHTML(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[char]));
}
export function number(value, digits = 2) {
  if (typeof value !== 'number' || !Number.isFinite(value)) return '—';
  return value.toLocaleString('en-US', {
    minimumFractionDigits: digits, maximumFractionDigits: digits
  });
}
export function change(value) {
  if (typeof value !== 'number' || !Number.isFinite(value)) return '—';
  const sign = value > 0 ? '+' : value < 0 ? '−' : '';
  return `${sign}${number(Math.abs(value), 2)}%`;
}
export function tone(lane) {
  const tones = {
    'Buy now': 'up', 'Almost ready': 'info', 'In favour': 'text',
    'Take profits': 'orange', 'Watch — don’t chase': 'warn', 'Stand aside': 'muted'
  };
  return Object.hasOwn(tones, lane) ? tones[lane] : 'muted';
}
