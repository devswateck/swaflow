---
title: 'SWAFLOW visual shell'
type: 'feature'
created: '2026-06-09'
status: 'in-review'
baseline_commit: '533ce87609109706230237ebe5629fd34c324fa9'
context:
  - '{project-root}/_bmad-output/project-context.md'
  - '{project-root}/_bmad-output/planning-artifacts/ux-designs/ux-Swaflow-2026-06-09/DESIGN.md'
  - '{project-root}/_bmad-output/planning-artifacts/ux-designs/ux-Swaflow-2026-06-09/EXPERIENCE.md'
  - '{project-root}/_bmad-output/planning-artifacts/ux-designs/ux-Swaflow-2026-06-09/frontend-implementation-brief.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** El frontend todavia se ve como un MVP verde/teal: usa `brand: #0f766e`, fondo `#edf3ef`, marca visible "Swatek Flow AI" y navegacion plana sin grupos. Esto contradice la direccion UX aprobada para `SWAFLOW`: dark mode por defecto, identidad Swa Tech magenta/violeta y una consola SaaS mas profesional.

**Approach:** Implementar la base visual y el shell global antes de tocar Dashboard o Inbox: tokens Tailwind Swa Tech, dark mode por defecto, login/loading/app shell con superficies oscuras legibles, marca `SWAFLOW` y sidebar agrupado por Operacion, Comercio, Automatizacion y Administracion. Los modulos actuales deben seguir funcionando con sus mismos datos y acciones.

## Boundaries & Constraints

**Always:** Mantener React/Vite/Tailwind actuales; conservar Zustand auth, `swaflow_theme`, `swaflow_active_page` y llamadas API existentes; mantener copy visible en espanol; usar lucide-react para iconos; respetar radios de 8px o menos; asegurar labels accesibles en botones solo-icono; hacer que dark mode sea el default solo cuando no exista preferencia guardada.

**Ask First:** Agregar assets finales de logo en `frontend/src/assets`; cambiar comportamiento funcional de navegacion, auth, permisos, API o rutas; modificar Dashboard o Inbox mas alla de heredar shell/tokens; introducir dependencias nuevas. Recharts esta aprobado para Dashboard, pero queda fuera de esta historia.

**Never:** No implementar el rediseno profundo de Dashboard; no implementar el rail contextual de Inbox; no crear datos falsos; no usar verde/teal como color de marca; no convertir toda la app en una superficie neon ilegible; no tocar backend, PRD ni spines UX en esta historia.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Usuario sin preferencia de tema | `localStorage.swaflow_theme` ausente | La app inicia en dark mode y guarda/aplica `theme-dark` sin romper login ni shell | Si localStorage no esta disponible, fallback visual dark desde CSS root |
| Usuario con preferencia clara | `swaflow_theme = "light"` | La app respeta light mode y el toggle permite volver a dark | Valor invalido se trata como dark |
| Navegacion desktop | Viewport `lg+` autenticado | Sidebar oscuro con grupos: Operacion, Comercio, Automatizacion, Administracion; item activo con acento magenta | Pagina activa invalida sigue cayendo a Dashboard |
| Navegacion mobile | Viewport menor a `lg` | Menu sheet oscuro/consistente, cierra con boton accesible y conserva grupos | Overlay no tapa acciones fuera del sheet al cerrar |
| Branding visible | Login, sidebar, loading | Texto visible `SWAFLOW`; no aparece "Swatek Flow AI" ni "SwaFlow" | Si no hay SVG final, usar monograma/lockup CSS vector-like, no PNG generado |

</frozen-after-approval>

## Code Map

- `frontend/tailwind.config.ts` -- Fuente de tokens Tailwind actuales; debe cambiar de verde/teal a Swa Tech manteniendo aliases existentes donde sea pragmatico.
- `frontend/src/styles.css` -- Root theme y parches dark actuales; debe pasar a dark default y tokens compatibles sin depender de `#edf3ef`.
- `frontend/src/App.tsx` -- Shell, login, loading, `Brand`, `Sidebar`, `NavList`, `getStoredTheme` y clases visuales globales.
- `frontend/package.json` -- Solo validar scripts; no requiere dependencia nueva para esta historia.

## Tasks & Acceptance

**Execution:**
- [x] `frontend/tailwind.config.ts` -- Reemplazar/expandir tokens `ink`, `line`, `panel`, `brand`, `warn`, `danger` con paleta Swa Tech y aliases como `brandNight`, `brandDeep`, `brandPanel`, `brandAccent`, `brandAccentSoft`, `inkMuted`, `surfaceMuted` -- Permite migrar clases sin reescribir todo el frontend.
- [x] `frontend/src/styles.css` -- Convertir dark mode en base por defecto, ajustar `:root`, `.theme-dark`, `.theme-light` y controles de formulario para superficies Swa Tech -- Evita parches verdes y permite que el toggle sea consistente.
- [x] `frontend/src/App.tsx` -- Cambiar `getStoredTheme` para default dark y valor invalido dark; actualizar app shell, login y loading a superficies/tokens nuevos -- Cumple decision de dark mode por defecto sin romper preferencia guardada.
- [x] `frontend/src/App.tsx` -- Reemplazar `Brand` por lockup `SWAFLOW` con monograma CSS/SVG inline simple y subtitulo "Ventas por WhatsApp" -- Evita depender del PNG concepto y corrige naming.
- [x] `frontend/src/App.tsx` -- Reestructurar `navItems` en grupos renderizados por `NavList`, manteniendo las mismas `PageKey` y callbacks -- Simplifica navegacion sin cambiar rutas ni comportamiento.
- [x] `frontend/src/App.tsx` -- Actualizar clases de header, mobile sheet, sidebar, active nav, botones globales y busqueda para retirar verdes visibles -- Establece shell profesional antes de redisenar paginas internas.

**Acceptance Criteria:**
- Given un usuario nuevo sin `swaflow_theme`, when abre login o app autenticada, then la superficie inicial es dark mode Swa Tech.
- Given `localStorage.swaflow_theme = "light"`, when se carga la app, then se respeta light mode y el toggle puede volver a dark.
- Given desktop `lg+`, when el usuario ve el sidebar, then la navegacion esta agrupada y Dashboard/Inbox aparecen en Operacion.
- Given mobile, when abre/cierra menu, then el sheet usa la misma agrupacion y tiene boton accesible de cierre.
- Given cualquier pantalla global, when se inspecciona branding visible, then aparece `SWAFLOW` y no queda `Swatek Flow AI`.
- Given una busqueda textual por colores/marca, when se revisa shell/nav/botones primarios, then no quedan `#0f766e`, `#e5f3ee` ni clases emerald como marca.

## Spec Change Log

## Design Notes

La primera implementacion del logo debe ser vector-like en codigo, no el PNG conceptual. Un monograma simple `S` o `SW` en un bloque oscuro con borde/acento magenta es suficiente para shell; el arte final SVG se puede reemplazar despues sin cambiar estructura.

La navegacion agrupada no debe cambiar `activePage` ni `localStorage.swaflow_active_page`; solo cambia presentacion:

```ts
const navGroups = [
  { label: "Operacion", items: [...] },
  { label: "Comercio", items: [...] },
];
```

## Verification

**Commands:**
- `cd frontend && npm run build` -- expected: TypeScript y build Vite exitosos.
- `cd frontend && npm run lint` -- expected: sin errores nuevos; si hay fallos preexistentes, documentarlos.

**Manual checks (if no CLI):**
- Revisar login, loading, app shell desktop y mobile: dark default, branding `SWAFLOW`, grupos de navegacion y sin acentos verdes.
