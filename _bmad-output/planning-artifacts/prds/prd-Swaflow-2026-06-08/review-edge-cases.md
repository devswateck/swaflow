# Revisión de casos límite - PRD de Swaflow

## Veredicto

El PRD cubre los caminos felices principales y varios caminos de error. Los casos límite restantes son más operativos y de integración que conceptuales.

## Hallazgos altos

1. **La autoasignación cuando existe un usuario adicional puede sorprender a los tenants.**
   - Ubicación: FR-021.
   - Riesgo: si existe exactamente un usuario adicional, todos los chats van a ese usuario por defecto, aunque el admin espere visibilidad compartida o cobertura temporal.
   - Fix recomendado: agregar override y visibilidad para admin: puede desactivar autoasignación, reasignar y ver todos los chats.

## Hallazgos medios

1. **El contexto al reactivar la IA necesita reglas de frontera.**
   - Ubicación: FR-014.
   - Riesgo: reactivar la IA después de intervención humana no debe hacer que contradiga promesas humanas ni repita el funnel de bienvenida.
   - Fix recomendado: indicar que la IA debe resumir/reusar el contexto humano reciente, evitar reejecutar el welcome cuando ya se completó y respetar compromisos registrados en el chat solo cuando no contradigan la verdad del backend.

2. **El seguimiento por expiración de pago necesita límite de cadencia.**
   - Ubicación: FR-145.
   - Riesgo: la IA podría spamear seguimientos después de la expiración.
   - Fix recomendado: agregar un límite configurable o por defecto, por ejemplo un solo seguimiento después del vencimiento salvo que el cliente responda.

3. **Las opciones de cita en días distintos pueden fallar con disponibilidad escasa.**
   - Ubicación: FR-150, FR-166.
   - Riesgo: en los próximos 7 días puede haber menos de tres días distintos disponibles.
   - Fix recomendado: definir fallback: proponer menos opciones con un mensaje claro, o permitir múltiples slots el mismo día si está configurado.

## Hallazgos bajos

1. **La reasignación manual de chats debería notificar o actualizar visiblemente al asignado anterior.**
   - Ubicación: FR-026.
   - Fix recomendado: exigir actualización/realtime cuando el admin reasigna.

2. **Los usuarios con acceso a Productos pero no a WhatsApp podrían ver el estado de sincronización Meta sin credenciales.**
   - Ubicación: Roles/Productos.
   - Fix recomendado: aclarar la visibilidad de solo lectura del catálogo versus el acceso a configuración de WhatsApp.
