# Revisión técnica del producto - PRD de Swaflow

## Veredicto

Adecuado para comenzar arquitectura después de un pequeño conjunto de aclaraciones. El PRD respeta las restricciones existentes del backend y evita mover la verdad crítica a n8n o a la IA. Los mayores riesgos de implementación son la abstracción de proveedores, la semántica de inventario desde Meta, el provisionamiento de tenants y la auditoría/exportación operativa.

## Hallazgos altos

1. **El provisionamiento de tenants está insuficientemente especificado.**
   - Ubicación: Product Scope, UJ-003.
   - Riesgo: el lanzamiento V1 necesita una vía operativa para crear tenants y admins incluso si el panel de SuperUsuario es V2.
   - Fix recomendado: declarar el provisionamiento V1 de tenants como proceso manual/operado por Swateck, con onboarding self-service y panel de operaciones de SuperUsuario en V2.

2. **La abstracción de pasarela de pago necesita un contrato V1.**
   - Ubicación: FR-110, FR-154, FR-145/146.
   - Riesgo: "el cliente puede implementar la pasarela que desee" puede disparar el alcance si V1 no define un modelo de adaptador.
   - Fix recomendado: definir un contrato de adaptador de proveedor: crear enlace de pago, expiración, validación de webhook, mapeo de estados, clave/referencia de idempotencia y semántica de reembolso/fallo/vencimiento si aplica.

## Hallazgos medios

1. **La disponibilidad de Meta puede no equivaler a cantidad reservable.**
   - Ubicación: FR-045 a FR-052.
   - Riesgo: si Meta entrega estado/disponibilidad pero no cantidad de stock, la matemática de reservas de Swaflow necesita una fuente local de cantidad o un comportamiento conservador.
   - Fix recomendado: especificar formas de disponibilidad soportadas: cantidad numérica cuando exista; de lo contrario estado de disponibilidad; si la cantidad es desconocida, la IA puede mostrar el producto pero el backend debe evitar reservas basadas en cantidad más allá de las reglas configuradas.

2. **El paquete de exportación necesita un conjunto mínimo de datos.**
   - Ubicación: FR-160.
   - Riesgo: soporte/offboarding quedará ambiguo.
   - Fix recomendado: el export mínimo incluye contactos, conversaciones/mensajes, órdenes, metadata de pagos, citas, eventos, snapshot de productos, inventario/reservas, actividad de usuario/auditoría, configuraciones de integraciones sin secretos y assets cargados.

3. **La disponibilidad de calendario necesita reglas de zona horaria y conflicto ligadas a la configuración del tenant.**
   - Ubicación: FR-147 a FR-166.
   - Riesgo: aunque existen buenos defaults, la arquitectura necesita granularidad de conflicto.
   - Fix recomendado: establecer que las propuestas usan la zona horaria del tenant, evitan traslapes con citas/eventos existentes y respetan la duración configurada en Citas.

## Hallazgos bajos

1. **El orden de los FR debería normalizarse antes de generar épicas.**
2. **El discovery intake debería degradarse antes de la publicación final.**
