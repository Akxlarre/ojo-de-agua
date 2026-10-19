# Skill: koa-error-learn

## Cuándo activar este skill

Actívalo **automáticamente** cuando el usuario:
- Pegue un error en el chat (TypeScript, Angular, Supabase, consola del navegador)
- Diga frases como: "tengo este error", "me salió esto", "falló el build", "la consola muestra"
- Muestre un stack trace, un código de error (TS2345, PGRST116, etc.) o un mensaje de excepción

No esperes que el usuario diga "/koa-error-learn" — detecta el patrón de error en el mensaje.

## Flujo de ejecución

### Paso 1 — Registrar el error en error-value.json

Ejecuta inmediatamente:

```bash
node scripts/error-value-manager.js --record --pattern "<texto_del_error>" --source <cli|browser|backend> --summary "<descripción_en_una_línea>"
```

- `--source cli` → errores de `ng build`, `ng serve`, `lint:arch`, TypeScript
- `--source browser` → errores de la consola del navegador, ExpressionChanged, NullInjector
- `--source backend` → errores de Supabase, RLS, Edge Functions, 401/403/500

### Paso 2 — Analizar y responder

1. Lee la salida del comando anterior (isNew, count, weight, code)
2. Si `weight >= 4` o `count >= 5`: menciona explícitamente que es un error **crítico/recurrente**
3. Busca en `indices/ANTI-PATTERNS.md` si el patrón ya tiene una solución documentada
4. Proporciona la solución siguiendo las reglas de arquitectura de `.claude/rules/`

### Paso 3 — Promoción a ANTI-PATTERNS (si count >= 10)

Si el error ha ocurrido 10 o más veces, agrega una entrada en `indices/ANTI-PATTERNS.md`:

```markdown
| [CÓDIGO] | Descripción del patrón | Solución canónica | Regla |
```

Y elimínalo de `error-value.json` (ya está "graduado" a memoria de largo plazo):

```bash
# Actualmente manual — futura automatización en error-value-manager.js --graduate
```

## Ejemplo de interacción

**Usuario:** "me sale esto: NullInjectorError: No provider for ProjectsFacade"

**Claude debe:**
1. Ejecutar: `node scripts/error-value-manager.js --record --pattern "NullInjectorError: No provider for ProjectsFacade" --source browser`
2. Identificar como `NG-NULL-INJ`, weight=3
3. Responder con la causa (falta `providers: [ProjectsFacade]` en el componente standalone) y la corrección exacta

## Privacidad

- `error-value.json` es **local** y está en `.gitignore`
- El usuario comparte voluntariamente con: `npm run koa:share-errors` (feature futura)
- **Nunca** incluir código fuente del usuario ni rutas del sistema en el pattern guardado — solo el mensaje de error genérico

## Referencia rápida de weights

| Weight | Significado | Ejemplo |
|--------|-------------|---------|
| 1 | Warning — no rompe nada | Bundle size exceeded |
| 2 | Error leve | Color hardcodeado, @Input() deprecated |
| 3 | Error recurrente que rompe features | ExpressionChanged, ARCH violation |
| 4 | Crash de runtime | BUILD FAILED, NullInjector |
| 5 | Pérdida de datos / seguridad | RLS bloqueado, Supabase auth error |
