/**
 * error-catalog.js
 *
 * Catálogo central de patrones de error con código normalizado y peso de severidad.
 * Weight: 1=warning, 2=error leve, 3=error recurrente, 4=crash, 5=pérdida de datos/RLS
 *
 * Importado por error-value-manager.js y error-monitor.js.
 * Para agregar nuevos patrones: añade una entrada al array CATALOG.
 */

export const CATALOG = [
  // ── Angular / TypeScript ─────────────────────────────────────────────────
  {
    code: 'TS-2345',
    pattern: /TS2345|Argument of type .+ is not assignable/,
    source: 'cli',
    weight: 2,
    category: 'typescript',
    hint: 'Incompatibilidad de tipos — revisa el modelo o el input del componente.',
  },
  {
    code: 'TS-2304',
    pattern: /TS2304|Cannot find name/,
    source: 'cli',
    weight: 2,
    category: 'typescript',
    hint: 'Símbolo no importado o no declarado.',
  },
  {
    code: 'TS-2339',
    pattern: /TS2339|Property .+ does not exist on type/,
    source: 'cli',
    weight: 2,
    category: 'typescript',
    hint: 'Acceso a propiedad inexistente — posible signal no inicializado.',
  },
  {
    code: 'NG-EXPR-CHANGED',
    pattern: /ExpressionChangedAfterItHasBeenCheckedError/,
    source: 'browser',
    weight: 3,
    category: 'angular',
    hint: 'Detección de cambios OnPush violada — usa signal() o async pipe.',
  },
  {
    code: 'NG-NULL-INJ',
    pattern: /NullInjectorError|No provider for/,
    source: 'browser',
    weight: 3,
    category: 'angular',
    hint: 'Servicio no provisto — verifica providers en el componente standalone.',
  },
  {
    code: 'NG-COMP-ERROR',
    pattern: /ERROR Error:|core\.mjs.*ERROR/,
    source: 'browser',
    weight: 4,
    category: 'angular',
    hint: 'Error de runtime en componente — revisa template y señales.',
  },

  // ── Arquitectura Koa (lint:arch) ─────────────────────────────────────────
  {
    code: 'ARCH-NGIF',
    pattern: /\*ngIf|\bngIf\b/,
    source: 'cli',
    weight: 3,
    category: 'architecture',
    hint: 'Usa @if en lugar de *ngIf (regla Koa).',
  },
  {
    code: 'ARCH-NGFOR',
    pattern: /\*ngFor|\bngFor\b/,
    source: 'cli',
    weight: 3,
    category: 'architecture',
    hint: 'Usa @for en lugar de *ngFor (regla Koa).',
  },
  {
    code: 'ARCH-INPUT-DEC',
    pattern: /@Input\(\)/,
    source: 'cli',
    weight: 3,
    category: 'architecture',
    hint: 'Usa input() signal en lugar de @Input() decorator (regla Koa).',
  },
  {
    code: 'ARCH-SUPABASE-UI',
    pattern: /SupabaseClient|createClient.*import.*app\/(shared|features)/,
    source: 'cli',
    weight: 5,
    category: 'architecture',
    hint: 'La UI no debe inyectar Supabase directamente — usa un Facade.',
  },
  {
    code: 'ARCH-HARDCOLOR',
    pattern: /text-(red|blue|green|yellow|pink|purple)-\d{3}|bg-\[#[0-9a-fA-F]+\]/,
    source: 'cli',
    weight: 2,
    category: 'visual',
    hint: 'Color hardcodeado — usa tokens semánticos (var(--ds-brand), text-primary).',
  },
  {
    code: 'ARCH-KEYFRAMES',
    pattern: /@keyframes|@angular\/animations/,
    source: 'cli',
    weight: 2,
    category: 'visual',
    hint: 'Usa GsapAnimationsService en lugar de CSS @keyframes o Angular animations.',
  },

  // ── Supabase / Backend ───────────────────────────────────────────────────
  {
    code: 'SB-RLS-401',
    pattern: /new row violates row-level security|RLS|401.*Unauthorized/,
    source: 'backend',
    weight: 5,
    category: 'security',
    hint: 'Política RLS bloqueó la operación — verifica que el usuario esté autenticado y la policy sea correcta.',
  },
  {
    code: 'SB-PGRST-116',
    pattern: /PGRST116|JSON object requested, multiple|Results contain \d+ rows/,
    source: 'backend',
    weight: 3,
    category: 'supabase',
    hint: 'La query devuelve múltiples filas donde se esperaba una — usa .maybeSingle() o filtra mejor.',
  },
  {
    code: 'SB-CONN',
    pattern: /Failed to fetch|NetworkError|ERR_CONNECTION_REFUSED.*supabase/i,
    source: 'backend',
    weight: 4,
    category: 'supabase',
    hint: 'No hay conexión a Supabase — verifica que el servidor local esté corriendo (npx supabase start).',
  },

  // ── Build / Webpack ──────────────────────────────────────────────────────
  {
    code: 'BUILD-CHUNK',
    pattern: /chunk .* exceeded the recommended size limit/,
    source: 'cli',
    weight: 1,
    category: 'build',
    hint: 'Bundle demasiado grande — considera lazy loading de módulos.',
  },
  {
    code: 'BUILD-FAIL',
    pattern: /BUILD FAILED|webpack compiled with \d+ error/i,
    source: 'cli',
    weight: 4,
    category: 'build',
    hint: 'El build falló — revisa los errores de TypeScript anteriores.',
  },
];

/**
 * Encuentra el primer patrón del catálogo que coincide con el texto dado.
 * @param {string} text
 * @returns {{ code: string, weight: number, category: string, hint: string, source: string } | null}
 */
export function matchError(text) {
  for (const entry of CATALOG) {
    if (entry.pattern.test(text)) {
      return {
        code: entry.code,
        weight: entry.weight,
        category: entry.category,
        hint: entry.hint,
        source: entry.source,
      };
    }
  }
  return null;
}
