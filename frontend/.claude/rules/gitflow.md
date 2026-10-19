---
name: Git Workflow & Conventional Commits
description: Branch naming, commit format (Conventional Commits), and when to commit
paths:
  - "src/**/*.ts"
  - "src/**/*.html"
  - "src/**/*.scss"
  - "supabase/**/*.sql"
---

# Reglas: Git Workflow

## Conventional Commits (obligatorio)

Formato: `<tipo>(<scope>): <descripción en imperativo>`

| Tipo | Cuándo |
|---|---|
| `feat` | Nueva funcionalidad visible para el usuario |
| `fix` | Corrección de un bug |
| `refactor` | Reestructuración sin cambio de comportamiento externo |
| `chore` | Dependencias, configuración, scripts, mantenimiento |
| `docs` | Solo documentación o comentarios |
| `test` | Solo tests — sin cambio de lógica de producción |
| `perf` | Optimización de rendimiento |
| `style` | Formato (espacios, comas) sin cambio de lógica |

**Scope** = módulo o feature afectado, en kebab-case.
Ejemplos válidos:
- `feat(instructor-dashboard): agregar KPI de clases completadas`
- `fix(auth-guard): corregir redirect en sesión expirada`
- `chore(deps): actualizar PrimeNG a 17.x`
- `refactor(alumnos-facade): extraer lógica de progreso a método privado`

## Cuándo crear un commit

Commitear después de completar cada **unidad lógica atómica**:
- Un componente nuevo funcional (con su template y lógica base)
- Un bug corregido y verificado
- Un método nuevo en un Facade con su integración al template
- Una migración SQL con su RLS correspondiente
- Una refactorización completa de un módulo

**NUNCA:**
- Commitear trabajo a medias (componente sin template, facade sin método)
- Mezclar múltiples features en un commit (`feat: dashboard + modal + tabla`)
- `git add .` sin revisar qué entra en staging (`git diff --staged` primero)
- Mensajes genéricos: "fix", "changes", "wip", "update"

## Estrategia de branches

```
main              ← producción. NUNCA push directo.
feature/<name>    ← funcionalidad nueva (desde main)
fix/<name>        ← corrección de bug (desde main)
refactor/<name>   ← reestructuración (desde main)
chore/<name>      ← mantenimiento (desde main)
```

Naming en kebab-case, descriptivo:
- `feature/instructor-ensayos-teoricos`
- `fix/auth-redirect-loop`
- `refactor/alumnos-facade-swr`
- `chore/upgrade-primeng-17`

## Flujo estándar de trabajo

```bash
# 1. Siempre partir desde main actualizado
git checkout main && git pull

# 2. Crear branch descriptiva
git checkout -b feature/<nombre>

# 3. Desarrollar en commits atómicos
git add <archivos-específicos>
git commit -m "feat(<scope>): descripción"

# 4. Subir branch
git push origin feature/<nombre>

# 5. Abrir PR → main (usar .github/PULL_REQUEST_TEMPLATE.md)
```

## Scripts disponibles

```bash
npm run claude:commit   # Claude agrupa cambios y crea commits Conventional
npm run claude:branch   # Claude crea la branch con nombre correcto
```

## PROHIBIDO

- `git push origin main` — sin PR
- Commits con mensaje de una palabra
- Un commit que toca features completamente independientes
- Squash de commits ajenos sin permiso del autor
