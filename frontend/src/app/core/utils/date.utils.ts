/**
 * Formats a Date to ISO date string (YYYY-MM-DD).
 */
export function toISODate(date: Date): string {
  return date.toISOString().split('T')[0];
}

/**
 * Formats a Date using Intl.DateTimeFormat.
 *
 * @param date - Date object or ISO string
 * @param locale - BCP 47 locale (default: 'en-US')
 * @param options - Intl.DateTimeFormatOptions (default: year numeric, month long, day numeric)
 */
export function formatDate(
  date: Date | string,
  locale = 'en-US',
  options?: Intl.DateTimeFormatOptions,
): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  return new Intl.DateTimeFormat(
    locale,
    options ?? { year: 'numeric', month: 'long', day: 'numeric' },
  ).format(d);
}

/**
 * Capitalizes the first letter of a string.
 */
export function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}
