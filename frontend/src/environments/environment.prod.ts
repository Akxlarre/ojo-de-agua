/**
 * environment.prod.ts — Configuración de producción.
 *
 * ⚠ NUNCA commitear claves reales aquí. Este archivo es el punto de entrada
 * para la configuración de producción — usa una de las opciones abajo.
 *
 * OPCIÓN A (recomendada para SPA estática — Vercel, Netlify, S3):
 *   Usa scripts/set-env.js para inyectar variables antes del build:
 *   ```
 *   node scripts/set-env.js && ng build --configuration=production
 *   ```
 *   set-env.js lee process.env.SUPABASE_URL y escribe este archivo en CI.
 *   Commitea ESTE archivo con valores vacíos — set-env.js lo sobrescribe en CI.
 *
 * OPCIÓN B (para SSR / servidor con control de headers):
 *   Lee las claves desde window._env_ inyectado por el servidor en index.html:
 *   ```html
 *   <script>window._env_ = { SUPABASE_URL: "...", SUPABASE_ANON_KEY: "..." };</script>
 *   ```
 *   Y lee con: (window as any)._env_?.SUPABASE_URL ?? ''
 *
 * NOTA: process.env no existe en el browser. Angular usa define() de esbuild
 * o la flag --define de Webpack para reemplazos en build-time.
 * Sin configuración adicional, deja estos valores como string vacío
 * y configúralos vía el script set-env.js mencionado arriba.
 */
export const environment = {
  production: true,
  supabase: {
    // Reemplazar por el script set-env.js en CI — no usar process.env directamente
    url: "",
    anonKey: "",
  },
};
