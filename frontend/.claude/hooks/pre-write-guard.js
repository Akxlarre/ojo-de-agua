#!/usr/bin/env node
/**
 * pre-write-guard.js — PreToolUse Hook (Edit|Write|MultiEdit)
 *
 * Sistema de guardrails que se ejecuta ANTES de cada escritura de archivo.
 * Cuatro capas de protección:
 *
 *   1. FILE PROTECTION    — Bloquea edits a archivos críticos del sistema de hooks
 *   2. DISCOVERY GATE     — Obliga a leer los índices antes de escribir código fuente
 *   3. ARCHITECT GUARD    — Validación rápida de reglas arquitectónicas en el contenido nuevo
 *   4. CONTEXT INJECTION  — Inyecta contexto relevante según el tipo de archivo
 *                           (con dedup de sesión: cada categoría se inyecta solo 1 vez)
 *
 * Exit codes:
 *   0 = permitir la operación (opcionalmente con additionalContext via JSON stdout)
 *   2 = bloquear la operación (stderr se envía a Claude como feedback)
 *
 * Salida JSON (cuando se permite):
 *   { hookSpecificOutput: { hookEventName: "PreToolUse", additionalContext: "..." } }
 */

const fs = require('fs');
const path = require('path');
const os = require('os');

// ─── Read stack from blueprint.json (fail-open) ──────────────────────────────
let STACK = { angular: true, tailwind: true, primeng: true, gsap: false, supabase: true };
try {
  const bpPath = path.join(process.cwd(), 'blueprint.json');
  if (fs.existsSync(bpPath)) {
    const bp = JSON.parse(fs.readFileSync(bpPath, 'utf8'));
    if (bp.stack && typeof bp.stack === 'object') STACK = { ...STACK, ...bp.stack };
  }
} catch { /* fail-open */ }

// SEC-04: Limit stdin to 10 MB to prevent memory exhaustion (DoS) from crafted hook inputs.
const MAX_STDIN_BYTES = 10 * 1024 * 1024;
let data = '';
let dataSize = 0;
process.stdin.on('data', chunk => {
  dataSize += chunk.length;
  if (dataSize > MAX_STDIN_BYTES) {
    process.stderr.write('pre-write-guard: stdin payload exceeds 10 MB limit — aborting (fail-open).\n');
    process.exit(0);
  }
  data += chunk;
});
process.stdin.on('end', () => {
  try {
    const input = JSON.parse(data);
    const filePath = input.tool_input?.file_path || input.tool_input?.path || '';
    const newContent = input.tool_input?.new_string || input.tool_input?.content || '';
    const toolName = input.tool_name || '';
    const sessionId = process.env.CLAUDE_SESSION_ID || 'default';
    const normalizedPath = filePath.replace(/\\/g, '/');

    // ═══════════════════════════════════════════════════════════════════════
    // 1. FILE PROTECTION — Archivos del sistema de guardrails
    // ═══════════════════════════════════════════════════════════════════════
    const protectedPatterns = [
      '.claude/hooks/',
      '.claude/settings.json',
      '.claude/settings.local.json',
      'scripts/architect.js',
    ];

    for (const pattern of protectedPatterns) {
      if (normalizedPath.includes(pattern)) {
        process.stderr.write(
          `\u{1F6E1}\u{FE0F} FILE PROTECTOR: ${path.basename(filePath)} es parte del sistema de guardrails.\n` +
          `No se permite modificar archivos en: ${pattern}\n` +
          `Si necesitas cambiar la configuracion de hooks, pide al humano que lo haga manualmente.`
        );
        process.exit(2);
      }
    }

    // ═══════════════════════════════════════════════════════════════════════
    // 2. DAY-0 GATE & DISCOVERY GATE — Leer y llenar contexto antes de escribir
    // ═══════════════════════════════════════════════════════════════════════
    const isSourceCode =
      (normalizedPath.includes('src/app/') && !normalizedPath.endsWith('.spec.ts')) ||
      normalizedPath.includes('supabase/migrations/');

    if (isSourceCode) {
      // 2A. Day-0 Context Gate (Obligar a llenar contexto)
      const contextFiles = [
        path.join(process.cwd(), 'context', 'domain.md'),
        path.join(process.cwd(), 'context', 'brief.md'),
        path.join(process.cwd(), 'indices', 'DATABASE.md')
      ];

      for (const ctxFile of contextFiles) {
        if (fs.existsSync(ctxFile)) {
          const content = fs.readFileSync(ctxFile, 'utf8');
          if (content.includes('status: PENDING') || content.includes('[PENDING]')) {
             process.stderr.write(
               `\u{1F6A7} DAY-0 GATE BLOQUEADO: No puedes escribir codigo fuente aun.\n` +
               `El archivo ${path.basename(ctxFile)} tiene secciones marcadas como PENDING.\n\n` +
               `**INSTRUCCION CRITICA PARA EL AGENTE:**\n` +
               `Deten lo que estas haciendo. Entrevista al usuario mediante chat para rellenar los datos faltantes en ${path.basename(ctxFile)}. ` +
               `Usa tus herramientas para sobrescribir ${path.basename(ctxFile)} quitando todos los tags [PENDING] y cambiando status a FILLED. Solo despues podras programar.`
             );
             process.exit(2);
          }
        }
      }

      // 2B. Discovery Gate (Obligar a leer índices)
      const flagPath = path.join(os.tmpdir(), `koa-discovery-${sessionId}.flag`);
      if (!fs.existsSync(flagPath)) {
        process.stderr.write(
          `\u{1F50D} DISCOVERY GATE: Lee cualquier archivo de indices/ antes de escribir codigo fuente.\n` +
          `Opciones: COMPONENTS | SERVICES | FACADES | MODELS | DATABASE | ANTI-PATTERNS | DIRECTIVES | STYLES | PIPES | LAYOUTS\n` +
          `El bloqueo se levanta automaticamente al leer cualquier indices/*.md`
        );
        process.exit(2);
      }
    }

    // ═══════════════════════════════════════════════════════════════════════
    // 3. ARCHITECT GUARD — Validación rápida de reglas en contenido nuevo
    // ═══════════════════════════════════════════════════════════════════════

    const violations = [];
    const warnings = [];

    // --- TypeScript / HTML checks (solo en src/app/) ---
    if (normalizedPath.includes('src/app/') && (normalizedPath.endsWith('.ts') || normalizedPath.endsWith('.html'))) {

      // Directivas Angular deprecadas
      if (newContent.includes('*ngIf'))
        violations.push('*ngIf → @if {}');
      if (newContent.includes('*ngFor'))
        violations.push('*ngFor → @for {}');
      if (/\[ngClass\]/.test(newContent))
        violations.push('[ngClass] → [class.nombre]="expr"');
      if (/\[ngStyle\]/.test(newContent))
        violations.push('[ngStyle] → [style.prop]="expr"');

      // Decoradores deprecados
      if (/@Input\s*\(/.test(newContent))
        violations.push('@Input() → input() signal');
      if (/@Output\s*\(/.test(newContent))
        violations.push('@Output() → output() signal');

      // ARCH-11: supabase.types.ts es auto-generado — no editar manualmente
      if (/core\/models\/supabase\.types\.ts/.test(normalizedPath))
        violations.push('[ARCH-11] supabase.types.ts es auto-generado → npm run supabase:types');

      // Import directo de Supabase en capa UI
      if (
        STACK.supabase &&
        (normalizedPath.includes('features/') || normalizedPath.includes('shared/')) &&
        newContent.includes('@supabase/supabase-js')
      )
        violations.push('@supabase/supabase-js en UI → usar FacadeService');

      // @angular/animations prohibido siempre
      if (newContent.includes('@angular/animations'))
        violations.push(
          STACK.gsap
            ? '@angular/animations → GsapAnimationsService'
            : '@angular/animations → CSS transitions o View Transitions API'
        );

      // OnPush check — solo para Write (archivo completo) en .component.ts
      if (
        toolName === 'Write' &&
        normalizedPath.endsWith('.component.ts') &&
        newContent.includes('@Component') &&
        !newContent.includes('OnPush')
      )
        violations.push('Falta ChangeDetectionStrategy.OnPush en @Component');

      // Colores Tailwind hardcodeados
      const hardcodedColorRe =
        /(?:text|bg|border|ring|from|to|via)-(?:red|blue|green|yellow|purple|pink|orange|teal|cyan|indigo|emerald|rose|amber|lime|sky|violet|fuchsia)-\d{2,3}/;
      if (hardcodedColorRe.test(newContent))
        violations.push('Color Tailwind hardcodeado → tokens: text-primary, bg-surface, var(--ds-brand)');

      // AP-H1: Tokens no canónicos — doble prefijo (bg-bg-*) o namespace -state- inexistente
      const nonCanonicalTokenRe =
        /\b(bg-bg-(base|surface|elevated|subtle|overlay)|(text|bg|border)-state-(success|warning|error|info))\b/;
      if (nonCanonicalTokenRe.test(newContent))
        violations.push('[AP-H1] Token no canónico → bg-bg-* (doble prefijo) o *-state-* no existen | Usar: bg-base, bg-surface, text-primary, text-muted, border-error');

      // Dumb component con inject de Facade
      if (normalizedPath.includes('shared/') && normalizedPath.endsWith('.component.ts')) {
        if (/inject\s*\(\s*\w*Facade/.test(newContent))
          violations.push('shared/ es Dumb: no inyectar Facades → mover lógica a features/');
      }

      // MessageService directo en componentes UI
      if (
        (normalizedPath.includes('features/') || normalizedPath.includes('shared/') || normalizedPath.includes('layout/')) &&
        normalizedPath.endsWith('.component.ts') &&
        /inject\s*\(\s*MessageService\s*\)/.test(newContent)
      )
        violations.push('inject(MessageService) → inject(ToastService) | Doc: notifications.md');

      // ARCH-12: Repository boundary — Facades no acceden a la BD directamente
      if (
        STACK.supabase &&
        normalizedPath.includes('.facade.') &&
        (/\bclient\.from\s*\(/.test(newContent) || /\bdb\.from\s*\(/.test(newContent))
      )
        violations.push('[ARCH-12] .db.from() en Facade → inject(XRepository) de core/repositories/ | Doc: facades.md');

      // LLM-01: Botones submit sin data-llm-action (solo en features/)
      if (normalizedPath.includes('features/')) {
        const submitBtnMatches = newContent.match(/<button[^>]*type="submit"[^>]*>/g) || [];
        const submitBtnsWithoutLlm = submitBtnMatches.filter(b => !b.includes('data-llm-action'));
        if (submitBtnsWithoutLlm.length > 0)
          violations.push('[LLM-01] <button type="submit"> sin data-llm-action | Doc: ai-readability.md');
      }

      // LLM-02: Botones destructivos sin data-llm-action (features/ y shared/)
      if (normalizedPath.includes('features/') || normalizedPath.includes('shared/')) {
        const destructiveBtnRe = /<button[^>]*aria-label="[^"]*(?:eliminar|delete|borrar|remove|remov)[^"]*"[^>]*>/gi;
        const destructiveBtns = newContent.match(destructiveBtnRe) || [];
        const destructiveBtnsWithoutLlm = destructiveBtns.filter(b => !b.includes('data-llm-action'));
        if (destructiveBtnsWithoutLlm.length > 0)
          violations.push('[LLM-02] Botón destructivo sin data-llm-action | Doc: ai-readability.md');
      }

      // M3: KPI ad-hoc — patrón que indica falta de .kpi-value (warning no bloqueante)
      if (/\b(text-4xl|text-3xl)\b.*font-(bold|black)/.test(newContent))
        warnings.push('[M3] text-4xl/3xl + font-bold/black → usar .kpi-value del design system | Doc: visual-system.md');
    }

    // --- A11Y checks (solo en templates HTML de src/app/) ---
    if (normalizedPath.includes('src/app/') && normalizedPath.endsWith('.html')) {
      const iconTagRe = /<app-icon(?![^>]*aria-label)[^>]*\/>/g;
      if (iconTagRe.test(newContent))
        violations.push('[A11Y-01] <app-icon> sin aria-label → [attr.aria-label]="X" o ariaHidden="true" | Doc: a11y-spec.md');

      const ptableRe = /<p-table\b(?![^>]*aria-label)[^>]*>/;
      if (ptableRe.test(newContent) && !newContent.includes('pTemplate="caption"'))
        violations.push('[A11Y-02] <p-table> sin aria-label ni caption | Doc: a11y-spec.md');
        
      if (normalizedPath.includes('features/') && newContent.includes('page-wide')) {
        violations.push('FAIL: Smart Component cannot use page-wide as root. Todo feature DEBE usar .bento-grid.');
      }
    }

    // --- SCSS / CSS checks (solo en src/) ---
    if (normalizedPath.includes('src/') && (normalizedPath.endsWith('.scss') || normalizedPath.endsWith('.css'))) {
      const isComponentStyle = normalizedPath.includes('src/app/');
      if (STACK.gsap && isComponentStyle && /@keyframes\s/.test(newContent))
        violations.push('@keyframes en componente (GSAP activo) → GsapAnimationsService o .indicator-live');

      const hardcodedColorRe =
        /(?:text|bg|border|ring)-(?:red|blue|green|yellow|purple|pink|orange|teal|cyan|indigo|emerald|rose|amber|lime|sky|violet|fuchsia)-\d{2,3}/;
      if (hardcodedColorRe.test(newContent))
        violations.push('Color Tailwind en SCSS → var(--ds-*) tokens');
    }

    // --- SEC-T03: Secrets in environment files ---
    if (normalizedPath.includes('src/environments/')) {
      const hasHardcodedJwt = /eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}/.test(newContent);
      const hasRealSupabaseUrl = /https:\/\/[a-z]{20}\.supabase\.co/.test(newContent);
      if (hasHardcodedJwt || hasRealSupabaseUrl)
        violations.push('[SEC] Credencial Supabase en environment file → usar variables de entorno en CI/CD');
    }

    // --- SQL migration checks ---
    if (normalizedPath.includes('supabase/migrations/')) {
      const fileName = path.basename(filePath);

      if (toolName === 'Write' && !/^\d{14}_\w+\.sql$/.test(fileName))
        violations.push('Nombre inválido → YYYYMMDDHHMMSS_dominio_tipo_descripcion.sql');

      if (/CREATE\s+TABLE/i.test(newContent) && !/ENABLE\s+ROW\s+LEVEL\s+SECURITY/i.test(newContent))
        violations.push('CREATE TABLE sin RLS → ALTER TABLE x ENABLE ROW LEVEL SECURITY;');
    }

    // --- Reportar violaciones ---
    if (violations.length > 0) {
      process.stderr.write(
        `\u{1F6A8} ARCHITECT GUARD: Violaciones detectadas en ${path.basename(filePath)}:\n` +
        violations.map(v => `  \u274C ${v}`).join('\n') +
        `\nCorrige el codigo antes de escribirlo.`
      );
      process.exit(2);
    }

    // ═══════════════════════════════════════════════════════════════════════
    // 4. CONTEXT INJECTION — Inyectar contexto relevante (con dedup de sesión)
    // ═══════════════════════════════════════════════════════════════════════
    // Cada categoría de archivo se inyecta UNA SOLA VEZ por sesión.
    // Las reglas arquitectónicas ya se cargan vía path-scoped rules (.claude/rules/).
    // Aquí solo se inyecta lo que las reglas no cubren: nombres de componentes
    // existentes, clases de botones, refs a índices, stack-specific reminders.

    // Determinar categoría de contexto para dedup
    const ctxCategory = normalizedPath.includes('features/') ? 'features'
      : normalizedPath.includes('shared/') ? 'shared'
      : normalizedPath.includes('layout/') ? 'layout'
      : normalizedPath.includes('core/repositories/') ? 'repositories'
      : normalizedPath.includes('core/facades/') ? 'facades'
      : normalizedPath.includes('core/services/') ? 'services'
      : normalizedPath.includes('core/utils/') ? 'utils'
      : normalizedPath.includes('core/directives/') ? 'directives'
      : normalizedPath.includes('supabase/migrations/') ? 'migrations'
      : normalizedPath.endsWith('.html') ? 'html'
      : (normalizedPath.endsWith('.scss') || normalizedPath.endsWith('.css')) ? 'scss'
      : null;

    // Dedup: si ya inyectamos esta categoría en esta sesión, salir sin contexto
    if (ctxCategory) {
      const ctxFlag = path.join(os.tmpdir(), `koa-ctx-${ctxCategory}-${sessionId}.flag`);
      if (fs.existsSync(ctxFlag)) {
        process.exit(0);
      }
      fs.writeFileSync(ctxFlag, new Date().toISOString());
    }

    const contextParts = [];

    // --- Componentes Angular (features/ o shared/) ---
    if (normalizedPath.endsWith('.component.ts')) {
      if (normalizedPath.includes('features/')) {
        contextParts.push(
          'SMART component (features/) — reglas completas en: architecture.md + visual-system.md.',
          'Componentes disponibles en shared/ (no recrear):',
          '  <app-kpi-card [value] label [trend] /> | <app-empty-state message /> | <app-alert-card title />',
          '  <app-drawer [isOpen] title /> | <app-icon name="kebab-case" [size]="20" /> | <skeleton-block variant />',
          'Clases de boton: btn-primary | btn-secondary | btn-ghost (definidas en tailwind.css).',
          'Toast: inject(ToastService) → toast.success() / toast.error(). NUNCA inject(MessageService).',
          ...(STACK.gsap
            ? ['Animaciones: inject(GsapAnimationsService) en ngAfterViewInit.']
            : ['Animaciones: CSS transitions (.animate-fade-in-up) o View Transitions API.']),
          'Layout: consulta LAYOUTS.md → identifica el arquetipo (dashboard/list/detail/form/auth/analytics/settings/onboarding) antes de estructurar la vista.',
          'Indices: COMPONENTS.md (que existe) | ANTI-PATTERNS.md (que evitar) | LAYOUTS.md (arquetipo de página).',
          '[CONTEXTO] context/domain.md — entidades y reglas de negocio del proyecto.',
          'Skills bajo demanda: /angular-component | /angular-signals | /design-system.',
          '[CONTEXTO] context/brief.md — objetivo de la sesión actual. context/domain.md — entidades del negocio.'
        );
      }
      if (normalizedPath.includes('shared/')) {
        contextParts.push(
          'DUMB component (shared/) — solo input() y output(). SIN inject() de Facades.',
          'Si recibe data async: crear {nombre}-skeleton.component.ts colocated.',
          'Clases semanticas (no Tailwind generico):',
          '  .kpi-value / .kpi-label | .surface-hero | .surface-glass | .indicator-live | .badge-pulse',
          '  .card / .card-accent (1 por seccion) / .card-tinted',
          'Iconos: <app-icon name="kebab-case" /> SIEMPRE. PROHIBIDO emojis o SVG inline.',
          'Indices: COMPONENTS.md (que existe) | ANTI-PATTERNS.md (que evitar).'
        );
      }
      if (normalizedPath.includes('layout/')) {
        contextParts.push(
          'LAYOUT component — puede inyectar services de core/ directamente.',
          'Dark mode: ThemeService con [data-mode="dark"]. PrimeNG: darkModeSelector ".fake-dark-mode".'
        );
      }
    }

    // --- Repositories ---
    if (normalizedPath.includes('core/repositories/') && normalizedPath.endsWith('.ts') && !normalizedPath.endsWith('.spec.ts')) {
      contextParts.push(
        'REPOSITORY (core/repositories/) — UNICO lugar donde se llama .db.from().',
        'Un metodo por query. Retorna datos tipados o null. NUNCA retorna el objeto Supabase raw.',
        'Naming: {dominio}.repository.ts. Interface del row colocada en el mismo archivo.',
        'Los Facades inyectan el Repository. La UI NUNCA lo inyecta directamente.',
        'DEBE tener .spec.ts companero (mockear SupabaseService con { db: clientMock }).'
      );
    }

    // --- Facades de dominio (core/facades/) ---
    if (normalizedPath.includes('core/facades/') && normalizedPath.endsWith('.ts') && !normalizedPath.endsWith('.spec.ts')) {
      contextParts.push(
        'FACADE DE DOMINIO (core/facades/) — reglas completas en: facades.md + swr-pattern.md (auto-cargadas).',
        'OBLIGATORIO extender BaseFacade<T> de @core/facades/base.facade.',
        'Inyectar Repositories (core/repositories/) para queries. NUNCA llamar .db.from() directamente.',
        'Mutaciones: patron optimistic-first (prev = _data(), optimistic update, catch → _data.set(prev)).',
        'Toast: inject(ToastService) para feedback. NUNCA inject(MessageService).',
        'DEBE tener .spec.ts companero.'
      );
    }

    // --- Core Services (core/services/) ---
    if (normalizedPath.includes('core/services/') && normalizedPath.endsWith('.ts') && !normalizedPath.endsWith('.spec.ts')) {
      if (normalizedPath.includes('.facade.')) {
        // AuthFacade — excepción documentada: no extiende BaseFacade, gestiona sesión
        contextParts.push(
          'AUTH FACADE (core/services/) — excepcion: gestiona sesion de usuario, no datos de dominio.',
          'No extiende BaseFacade. Usa onAuthStateChange() de SupabaseService.',
          'Los Facades de dominio van en core/facades/, no aqui.'
        );
      } else if (normalizedPath.includes('.service.')) {
        contextParts.push(
          'CORE SERVICE — la UI NUNCA lo inyecta directamente (solo via Facades).',
          'RxJS para flujos async internos. DEBE tener .spec.ts companero.'
        );
      }
    }

    // --- Migraciones SQL ---
    if (normalizedPath.includes('supabase/migrations/')) {
      contextParts.push(
        'MIGRACION SQL — reglas completas en: database.md (auto-cargada).',
        'Naming: YYYYMMDDHHMMSS_dominio_tipo_descripcion.sql',
        'Idempotente: CREATE TABLE IF NOT EXISTS. SIEMPRE: ALTER TABLE x ENABLE ROW LEVEL SECURITY;',
        'Documenta la tabla nueva en indices/DATABASE.md.'
      );
    }

    // --- Templates HTML ---
    if (normalizedPath.includes('src/app/') && normalizedPath.endsWith('.html')) {
      contextParts.push(
        'Template Angular — reglas completas en: architecture.md + ai-readability.md (auto-cargadas).',
        'Control flow: @if / @for / @switch. Bindings: [class.x] / [style.x].',
        'Semántica IA: data-llm-action en botones de mutación | data-llm-description en inputs críticos.',
        'Iconos: <app-icon name="..." /> SIEMPRE. Botones: btn-primary | btn-secondary | btn-ghost.',
        ...(STACK.gsap
          ? ['Bento: .bento-grid + [appBentoGridLayout]. Animaciones: GsapAnimationsService.']
          : ['Bento: .bento-grid + [appBentoGridLayout]. Animaciones: .animate-fade-in-up.']),
        'PrimeNG: imports standalone (Button, Select, Table — no modules).'
      );
    }

    // --- Estilos SCSS ---
    if (normalizedPath.includes('src/') && (normalizedPath.endsWith('.scss') || normalizedPath.endsWith('.css'))) {
      contextParts.push(
        'Estilos — reglas completas en: visual-system.md (auto-cargada).',
        'Tokens: var(--*) de _variables.scss. NO hex hardcodeados.',
        'Layouts: .page-centered / .page-narrow / .page-wide. Grids: .bento-grid.',
        ...(STACK.gsap
          ? ['Motion en src/app/: NO @keyframes. GSAP para entradas, View Transitions para rutas.']
          : ['Motion: @keyframes permitido. Clases: .animate-fade-in-up / .animate-fade-in / .animate-stagger.']),
        'Consulta indices/STYLES.md para lista completa de tokens y helpers.'
      );
    }

    // --- Pure Utils ---
    if (normalizedPath.includes('core/utils/') && normalizedPath.endsWith('.ts') && !normalizedPath.endsWith('.spec.ts')) {
      contextParts.push(
        'FUNCION PURA (core/utils/) — sin inject(), sin signal(), sin side effects.',
        'Naming: {dominio}.utils.ts. Export via barrel core/utils/index.ts.',
        'DEBE tener .spec.ts companero.'
      );
    }

    // --- Directivas ---
    if (normalizedPath.includes('core/directives/') && normalizedPath.endsWith('.ts')) {
      contextParts.push(
        'DIRECTIVA (core/directives/) — documentar en indices/DIRECTIVES.md.',
        'Usar host bindings, inject() para DI.'
      );
    }

    // --- Prepend warnings M3 como contexto no bloqueante ---
    if (warnings.length > 0) {
      contextParts.unshift(
        '⚠️ SUGERENCIA (no bloqueante):\n' + warnings.map(w => `  ⚡ ${w}`).join('\n')
      );
    }

    // --- Emitir contexto si hay algo relevante ---
    if (contextParts.length > 0) {
      // Si existe memoria de fallos del linter, mencionar
      try {
        const lessonsPath = path.join(process.cwd(), '.claude', 'temp', 'LESSONS_LEARNED.md');
        if (fs.existsSync(lessonsPath)) {
          contextParts.push(
            '[MEMORIA] .claude/temp/LESSONS_LEARNED.md existe — revisa patrones que ya fallaron antes de repetirlos.'
          );
        }
      } catch (_) { /* ignore */ }

      const context = contextParts.join('\n');
      const output = JSON.stringify({
        hookSpecificOutput: {
          hookEventName: 'PreToolUse',
          additionalContext: context
        }
      });
      process.stdout.write(output);
    }

    process.exit(0);
  } catch (e) {
    // Si el hook falla por error interno, permitir la operación (fail-open)
    process.exit(0);
  }
});
