#!/usr/bin/env node
/**
 * scripts/set-env.js — Inyecta variables de entorno en environment.prod.ts antes del build.
 *
 * Uso en CI/CD:
 *   node scripts/set-env.js && ng build --configuration=production
 *
 * Variables requeridas en el entorno:
 *   SUPABASE_URL       — URL del proyecto Supabase (ej: https://xxxx.supabase.co)
 *   SUPABASE_ANON_KEY  — Anon/public key del proyecto
 *
 * Si alguna variable falta, el script falla con exit(1) para no hacer build con creds vacías.
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const envProdPath = path.join(__dirname, '..', 'src', 'environments', 'environment.prod.ts');

const url = process.env.SUPABASE_URL;
const anonKey = process.env.SUPABASE_ANON_KEY;

if (!url || !anonKey) {
  console.error('❌  set-env.js: faltan variables de entorno requeridas.');
  console.error('   SUPABASE_URL:', url ? '✓' : '✗ MISSING');
  console.error('   SUPABASE_ANON_KEY:', anonKey ? '✓' : '✗ MISSING');
  console.error('');
  console.error('   Configura estas variables en tu CI/CD o en un archivo .env antes de hacer build.');
  process.exit(1);
}

const content = `export const environment = {
  production: true,
  supabase: {
    url: '${url}',
    anonKey: '${anonKey}',
  },
};
`;

fs.writeFileSync(envProdPath, content, 'utf8');
console.log('✅  environment.prod.ts configurado correctamente.');
console.log('   SUPABASE_URL:', url);
console.log('   SUPABASE_ANON_KEY:', anonKey.slice(0, 12) + '...');
