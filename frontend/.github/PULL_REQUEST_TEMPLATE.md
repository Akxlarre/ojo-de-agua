## ¿Qué hace este PR?

<!-- Una línea clara: qué problema resuelve o qué funcionalidad agrega. -->

## Tipo de cambio

- [ ] `feat` — nueva funcionalidad
- [ ] `fix` — corrección de bug
- [ ] `refactor` — reestructuración sin cambio de comportamiento
- [ ] `chore` — mantenimiento, dependencias, configuración
- [ ] `docs` — solo documentación
- [ ] `test` — solo tests

## Cambios principales

<!--
Lista los archivos/módulos clave tocados. No copies el diff — describe la intención.
- `src/app/features/X` — nuevo componente Y que hace Z
- `src/app/core/facades/X.facade.ts` — método nuevo `loadZ()`
- `supabase/migrations/XXXX_...sql` — tabla nueva para Z
-->

## Plan de pruebas

- [ ] `ng build` sin errores
- [ ] `npm run lint:arch` pasa sin violaciones
- [ ] `npm run test:ci` verde
- [ ] Flujo principal probado manualmente en `ng serve`
- [ ] Estados de error y loading verificados

## Screenshots / Evidencia

<!-- Adjunta capturas si hay cambios visuales. Elimina esta sección si no aplica. -->

## Checklist

- [ ] Sigue Conventional Commits en los mensajes de commit
- [ ] No hay colores hardcodeados ni imports de Supabase en componentes UI
- [ ] Los índices (`indices/`) están actualizados con componentes/servicios nuevos
- [ ] No hay `console.log` de debug olvidados
