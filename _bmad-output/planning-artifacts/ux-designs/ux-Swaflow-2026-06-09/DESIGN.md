---
name: SWAFLOW Swa Tech
description: Interfaz SaaS corporativa para ventas por WhatsApp asistidas por IA. Actualiza el MVP React/Tailwind desde verde a identidad Swa Tech oscura-magenta-violeta.
status: final
sources:
  - imports/swa-tech-logo-reference.md
  - brand/logo-brief.md
  - brand/swaflow-logo-concept-v1.png
  - ../../prds/prd-Swaflow-2026-06-08/prd.md
  - ../../../../frontend/src/App.tsx
  - ../../../../frontend/src/styles.css
  - ../../../../frontend/tailwind.config.ts
updated: 2026-06-10
colors:
  background: '#F6F7FB'
  surface: '#FFFFFF'
  surface-muted: '#EEF0F6'
  surface-raised: '#FFFFFF'
  ink: '#14111F'
  ink-muted: '#6D6A7A'
  ink-subtle: '#9691A6'
  line: '#DADDE8'
  brand-night: '#0B0614'
  brand-deep: '#160A24'
  brand-panel: '#211833'
  brand-primary: '#A855F7'
  brand-accent: '#FF3DE8'
  brand-accent-soft: '#F1D9FF'
  brand-on-dark: '#F8F2FF'
  action: '#7C3AED'
  action-hover: '#6D28D9'
  action-foreground: '#FFFFFF'
  info: '#2563EB'
  success: '#0891B2'
  warning: '#F59E0B'
  danger: '#E11D48'
  background-dark: '#0B0614'
  surface-dark: '#151023'
  surface-muted-dark: '#211833'
  surface-raised-dark: '#1A1129'
  ink-dark: '#F8F2FF'
  ink-muted-dark: '#BFB5D1'
  line-dark: '#332646'
  action-dark: '#FF3DE8'
  action-hover-dark: '#E936D4'
  focus-ring: '#FF3DE8'
typography:
  display:
    fontFamily: 'Sora, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: 32px
    fontWeight: '700'
    lineHeight: '1.15'
    letterSpacing: '0'
  page-title:
    fontFamily: 'Sora, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: 20px
    fontWeight: '700'
    lineHeight: '1.25'
    letterSpacing: '0'
  section-title:
    fontFamily: 'Sora, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: 15px
    fontWeight: '700'
    lineHeight: '1.35'
    letterSpacing: '0'
  body:
    fontFamily: 'Sora, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.55'
    letterSpacing: '0'
  label:
    fontFamily: 'Sora, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: 12px
    fontWeight: '600'
    lineHeight: '1.35'
    letterSpacing: '0'
  caption:
    fontFamily: 'Sora, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: 12px
    fontWeight: '400'
    lineHeight: '1.4'
    letterSpacing: '0'
rounded:
  sm: 4px
  md: 6px
  lg: 8px
  full: 9999px
spacing:
  '1': 4px
  '2': 8px
  '3': 12px
  '4': 16px
  '5': 20px
  '6': 24px
  '8': 32px
  gutter-desktop: 32px
  sidebar: 280px
components:
  app-shell:
    background: '{colors.background}'
    foreground: '{colors.ink}'
    dark-background: '{colors.background-dark}'
    dark-foreground: '{colors.ink-dark}'
  sidebar:
    background: '{colors.brand-night}'
    foreground: '{colors.brand-on-dark}'
    border: '{colors.line-dark}'
    width: '{spacing.sidebar}'
  nav-item-active:
    background: '{colors.brand-panel}'
    foreground: '{colors.brand-on-dark}'
    accent: '{colors.brand-accent}'
    radius: '{rounded.md}'
  nav-item-idle:
    foreground: '{colors.ink-muted-dark}'
    hover-background: '{colors.brand-panel}'
  button-primary:
    background: '{colors.action}'
    foreground: '{colors.action-foreground}'
    hover-background: '{colors.action-hover}'
    radius: '{rounded.md}'
  button-primary-dark:
    background: '{colors.action-dark}'
    foreground: '{colors.brand-night}'
    hover-background: '{colors.action-hover-dark}'
    radius: '{rounded.md}'
  card:
    background: '{colors.surface}'
    border: '{colors.line}'
    radius: '{rounded.lg}'
  card-dark:
    background: '{colors.surface-dark}'
    border: '{colors.line-dark}'
    radius: '{rounded.lg}'
  metric-card:
    background: '{colors.surface}'
    border: '{colors.line}'
    accent: '{colors.brand-accent}'
    radius: '{rounded.lg}'
  chart-panel:
    background: '{colors.surface}'
    grid-line: '{colors.line}'
    primary-series: '{colors.brand-accent}'
    secondary-series: '{colors.info}'
    tertiary-series: '{colors.warning}'
  chat-list-item-active:
    background: '{colors.brand-accent-soft}'
    border-left: '{colors.brand-accent}'
  chat-bubble-customer:
    background: '{colors.surface-muted}'
    foreground: '{colors.ink}'
    radius: '{rounded.lg}'
  chat-bubble-agent:
    background: '{colors.action}'
    foreground: '{colors.action-foreground}'
    radius: '{rounded.lg}'
  chat-bubble-ai:
    background: '{colors.brand-night}'
    foreground: '{colors.brand-on-dark}'
    accent: '{colors.brand-accent}'
    radius: '{rounded.lg}'
  status-success:
    background: '#E6F7FB'
    foreground: '{colors.success}'
    border: '#B7E8F2'
  status-warning:
    background: '#FFF7E6'
    foreground: '#B45309'
    border: '#FDE1A7'
  status-danger:
    background: '#FFF1F4'
    foreground: '{colors.danger}'
    border: '#FFD0DA'
---

## Marca y estilo

SWAFLOW es un SaaS operacional para ventas conversacionales por WhatsApp. La interfaz debe sentirse precisa, comercial y controlada: una consola de trabajo para equipos que gestionan clientes, ordenes, pagos, citas, funnels e IA.

La imagen Swa Tech aporta la identidad corporativa: base oscura tactica, marca blanca/lila y energia magenta/violeta. En la app, esa identidad debe convertirse en un sistema de producto disciplinado. Oscuro, magenta y violeta son la firma de marca; superficies neutras, tablas legibles, jerarquia clara y controles sobrios son la capa operativa.

Dark mode es el tema por defecto. Light mode queda como alternativa operativa para usuarios que prefieran mayor luminosidad durante jornadas largas, pero la expresion principal de marca vive en dark mode.

## Colores

- **Brand Night (`#0B0614`)** ancla la identidad Swa Tech. Usar como fondo base del tema por defecto, sidebar desktop, identidad del chat IA y zonas de marca de alta jerarquia. En light mode, usarlo con mas restriccion.
- **Brand Accent (`#FF3DE8`)** viene de la barra y aro del logo. Usar para foco, seleccion, acentos de grafica, focus ring y un enfasis principal por panel.
- **Brand Primary (`#A855F7`)** acompana al magenta como violeta estable. Usar para enfasis secundario, detalles de marca y estados visuales de baja frecuencia.
- **Action (`#7C3AED`)** es el color principal de botones en light mode. Es mas estable que el neon magenta para acciones diarias.
- **Sistema neutro** (`background`, `surface`, `surface-muted`, `line`, `ink`) hace la mayor parte del trabajo visual. Estos tokens mantienen profesionalismo y evitan ruido.
- **Estados** evitan la paleta verde rechazada. Success usa cyan/azul (`#0891B2`), warning usa amber y danger usa rose. Pagos e inventario deben seguir siendo semanticamente claros.

Evitar: acentos verdes/teal, grandes gradientes morados, blobs decorativos, texto neon en areas blancas amplias y usar magenta en todos los botones o badges.

## Tipografía

Usar Sora en toda la app. SWAFLOW es una interfaz operacional densa; la tipografia debe priorizar escaneo, alineacion y lectura rapida.

- `display` se reserva para estados vacios, paneles de onboarding/salud y resumenes especiales de Dashboard.
- `page-title` se usa en el header de pagina.
- `section-title` se usa en tarjetas, paneles, tablas y rails.
- `body`, `label` y `caption` gobiernan todo contenido operacional repetido.

Letter spacing permanece en `0`. No usar labels mayusculos espaciados dentro de controles densos; el logo puede cargar ese estilo, pero la aplicacion debe ser legible.

## Diseño y espaciado

Usar ritmo basado en 8px con densidad SaaS compacta. Tarjetas y paneles deben sentirse organizados, no editoriales.

- Shell desktop: sidebar agrupado fijo de `{spacing.sidebar}`, header superior y gutter `{spacing.gutter-desktop}`.
- Shell desktop: sidebar agrupado fijo/sticky de `{spacing.sidebar}`; el panel izquierdo permanece visible mientras el contenido principal scrolla.
- Dashboard: grid responsivo de 12 columnas. KPI primero, graficas segundo, listas operativas debajo o al costado.
- Inbox desktop: tres zonas - lista de conversaciones, hilo de mensajes y rail de contexto/acciones.
- Tablas: columnas estables, headers claros, scroll horizontal solo cuando sea inevitable.

No poner cards dentro de cards. Las secciones de pagina deben ser areas de contenido; las cards son para items repetidos, paneles y herramientas enfocadas.

## Elevación y profundidad

La profundidad debe ser sobria. Usar bordes y capas tonales primero, sombra despues.

- Cards en light mode usan `border: {colors.line}` y sombra muy sutil solo en paneles elevados.
- Cards en dark mode usan separacion tonal con `{colors.surface-dark}` y `{colors.line-dark}`.
- El acento de marca puede aparecer como borde izquierdo, regla superior, indicador seleccionado o serie de grafica.

Evitar sombras pesadas, contenedores brillantes y fondos decorativos.

## Formas

Los radios son precisos y profesionales:

- `{rounded.sm}` para controles compactos.
- `{rounded.md}` para botones, nav items, inputs y badges.
- `{rounded.lg}` para cards y paneles mayores.
- `{rounded.full}` solo para avatars, contadores no leidos y dots pequenos.

El logo usa circulo, pero la aplicacion no debe convertir circulos en patron general.

## Componentes

- **App shell** - Dark mode usa `{colors.background-dark}`, `{colors.surface-dark}` y `{colors.brand-night}` por defecto. Light mode usa `{colors.background}` y `{colors.surface}` como alternativa.
- **Brand lockup** - Reemplazar el sparkle verde por tratamiento SWAFLOW. El concepto v1 vive en `brand/swaflow-logo-concept-v1.png`; antes de produccion debe redibujarse como SVG. Usar lockup horizontal en login/sidebar expandido y monograma en favicon/loading/sidebar compacto.
- **Nav agrupada** - Usar etiquetas para Operacion, Comercio, Automatizacion, Administracion. Activo usa `{components.nav-item-active.background}` y borde/acento `{colors.brand-accent}`.
- **Primary button** - Usar `{colors.action}` en light mode y `{colors.action-dark}` en dark mode. Reservar neon para foco, no para cada boton.
- **Metric card** - Titulo KPI, valor, delta de periodo y mini trend. El acento es regla fina o linea pequena, no fill neon.
- **Chart panel** - Card clara/oscura con grid sutil, leyenda clara, una serie magenta primaria, una azul secundaria y amber solo para warning/comparacion.
- **Conversation list item** - Contacto, telefono, ultimo mensaje, no leidos, responsable, estado y funnel/paso. El item activo tiene acento izquierdo, no relleno verde.
- **Message bubble** - Cliente: neutro muted. Asesor humano: violeta action. IA: brand night con acento magenta o label bot. Incluir timestamp y tipo de emisor en caption.
- **Conversation context rail** - Panel derecho estable para estado IA, responsable, funnel/paso, orden/pago, cita, datos del cliente y acciones rapidas.
- **Status badge** - Color semantico por estado. Confirmado usa cyan/azul, espera usa amber, error usa rose. Mantener copy en espanol.
- **Data table** - Header en superficie muted, filas con hover, badges compactos y accion principal al final de fila.

## Lo que se debe y no se debe hacer

| Do | Don't |
|---|---|
| Reemplazar todo uso verde de marca por tokens Swa Tech | Mantener `#0f766e`, `#e5f3ee` o emerald como marca |
| Usar magenta/violeta como acentos de seleccion, foco y graficas | Inundar cada panel con morado o magenta |
| Mantener cards con radio maximo de 8px | Usar cards muy redondeadas o cards anidadas |
| Hacer graficas de Dashboard legibles y data-first | Usar graficas decorativas sin labels, leyenda o ejes |
| Mover acciones de Inbox a un rail contextual | Dejar acciones criticas como botones sueltos bajo el hilo |
| Usar dark mode como tema por defecto con superficies legibles | Convertir dark mode en una masa morada sin contraste ni jerarquia |
| Mantener microcopy espanol directo y operacional | Agregar slogans de marketing dentro del flujo |
