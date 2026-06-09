---
project: Swaflow
status: draft-ready-for-frontend-agent
updated: 2026-06-09
sources:
  - DESIGN.md
  - EXPERIENCE.md
  - brand/logo-brief.md
  - brand/swaflow-logo-concept-v1.png
  - ../../../../frontend/src/App.tsx
  - ../../../../frontend/src/styles.css
  - ../../../../frontend/tailwind.config.ts
---

# Brief de implementacion frontend

Usar `DESIGN.md` y `EXPERIENCE.md` como contrato UX. Este brief traduce esos spines a una primera pasada practica para el frontend.

## Alcance de primera pasada

1. Reemplazar el sistema visual verde por tokens Swa Tech.
2. Simplificar navegacion con grupos en el sidebar.
3. Rediseniar Dashboard como consola comercial profesional.
4. Rediseniar Inbox como workspace de chat mas completo.
5. Mantener llamadas API y comportamiento de negocio estables salvo aprobacion explicita para backend.

## Archivos a inspeccionar primero

- `frontend/src/App.tsx` - shell actual, paginas y componentes compartidos.
- `frontend/src/styles.css` - estilos globales y parches de dark mode.
- `frontend/tailwind.config.ts` - sistema actual de tokens verdes.
- `frontend/src/lib/api.ts` - helper API y manejo de errores.
- `frontend/src/lib/auth.ts` - store de auth y token.

## Orden de implementacion

1. Actualizar tokens Tailwind:
   - Reemplazar `brand: "#0f766e"` con valores Swa Tech desde `DESIGN.md`.
   - Agregar `brandNight`, `brandDeep`, `brandPanel`, `brandAccent`, `brandAccentSoft`, `inkMuted`, `surfaceMuted`.
   - Mantener aliases semanticos estables donde ayude a migrar gradualmente.

2. Actualizar estilos globales:
   - Reemplazar parches verde/dark-mode por superficies compatibles con tokens.
   - Quitar supuestos especificos como `.theme-dark .bg-[#edf3ef]` cuando los componentes usen tokens.
   - Preservar mensajes visibles en espanol.

3. Estandarizar primitivos compartidos dentro de `App.tsx` o extraidos:
   - `Button`
   - `Card`
   - `Badge`
   - `PageHeader`
   - `Sidebar`
   - `SectionHeader`
   - `DataTable`
   - `MessageBubble`
   - `EmptyState`
   - `Skeleton`

4. Rediseniar shell:
   - Sidebar desktop oscuro Swa Tech.
   - Grupos nav: Operacion, Comercio, Automatizacion, Administracion.
   - Item activo con acento izquierdo magenta.
   - Header compacto con busqueda, tema, notificaciones y cuenta.
   - Reemplazar el label actual "Swatek Flow AI" por `SWAFLOW`.
   - Hacer dark mode el default cuando no exista preferencia guardada en localStorage.
   - Usar el concepto de logo como referencia visual, pero implementar preferiblemente SVG/vector cuando exista arte final.

5. Rediseniar Dashboard:
   - KPI row: chats que requieren accion, pagos pendientes, ventas confirmadas, citas de hoy.
   - Agregar delta/trend donde exista dato; si no, mostrar "Sin comparativo".
   - Reemplazar "Flujo de compra" por panel profesional de conversion/funnel.
   - Agregar paneles de grafica usando datos existentes primero:
     - Chats en el tiempo.
     - Ventas/ordenes por estado.
     - Citas por fecha/estado.
   - Agregar banda de salud: WhatsApp, IA, Catalogo, Pagos, Calendario.
   - Agregar cola de atencion: chats no leidos, waiting payment, bajo/sin stock si hay dato, proximas citas.

6. Rediseniar Inbox:
   - Layout desktop: lista de conversaciones, hilo de chat, rail de contexto.
   - Filas de lista muestran contacto, telefono, no leidos, estado, responsable, funnel/paso, ultimo mensaje y tiempo si existe.
   - Header de chat muestra contacto, telefono, status, responsable y estado IA/humano.
   - Burbujas distinguen cliente, asesor humano e IA/system cuando el dato lo permita.
   - Mover "Pasar a humano", "Agendar cita", selectores de funnel y paso al rail.
   - Composer preserva draft cuando falla y muestra error inline.
   - Estados vacio/no seleccionado siguen `EXPERIENCE.md`.

7. Mantener modulos funcionales:
   - Productos, Inventario, Ordenes, Citas, Funnels, IA, WhatsApp, Integraciones y Ajustes pueden recibir refresh visual de tokens en primera pasada.
   - Evitar reconstruir todos los flujos de modulo salvo pedido explicito.

## Guia de datos y dependencias

- No inventar datos backend.
- Si no existe time series lista para graficas, derivar resumenes simples desde arrays actuales y etiquetarlos honestamente.
- Agregar y usar Recharts para las graficas del Dashboard: line charts, bar charts, areas, tooltips, leyendas y ejes responsivos.
- Mantener aislamiento tenant. Frontend nunca salta scoping de API.

## Checklist de aceptacion

- No quedan acentos verdes/teal visibles en shell, nav, botones, estados activos, burbujas, progress bars o foco.
- Dashboard tiene paneles tipo grafica con datos reales o estados vacios honestos, no placeholders decorativos.
- Inbox desktop tiene rail de contexto/acciones estable.
- Navegacion esta agrupada y es mas escaneable.
- Dark mode sigue funcionando y se siente intencional.
- Dark mode es el tema inicial por defecto.
- Texto cabe en botones, nav items, cards y filas de chat en mobile y desktop.
- Botones solo-icono tienen nombres accesibles.
- `npm run build` pasa.
- `npm run lint` pasa o se documentan issues preexistentes.
