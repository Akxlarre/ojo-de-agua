export type UserRole = 'admin' | 'member' | 'secretaria' | 'instructor' | 'alumno' | 'relator';

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  initials: string;
  avatarUrl?: string;
  dbId?: string | number;
  firstLogin?: boolean;
  branchId?: string | number;
  isActive?: boolean;
}

/**
 * Genera iniciales desde display_name (ej: "María López" -> "ML").
 */
export function getInitialsFromDisplayName(displayName: string): string {
  // SEC: cap at 200 chars before splitting to prevent DoS with huge display_name values
  // stored directly via API (e.g. thousands of spaces creating a massive array).
  const safe = String(displayName ?? '').slice(0, 200);
  const parts = safe.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}
