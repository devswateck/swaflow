# Research: WhatsApp Onboarding

## Pregunta

Como simplificar la conexion de cuentas WhatsApp/Meta para clientes multi-tenant.

## Hallazgos

- La ruta recomendada para SaaS que conectan cuentas de clientes es Embedded Signup/Facebook Login for Business, no pedir tokens manuales como experiencia principal.
- El flujo embebido permite que el cliente autentique con Meta, seleccione o cree activos WhatsApp y conceda permisos a la app.
- Tras completar el flujo, el backend debe intercambiar el codigo por token/credenciales, guardar IDs de WABA y numero, registrar/verificar el numero y configurar webhooks segun el modelo de permisos aprobado.
- Para operar como proveedor con clientes externos, la app Meta necesita revision y acceso avanzado a permisos relevantes; al menos `whatsapp_business_management` y `whatsapp_business_messaging` segun el alcance de envio/recepcion y gestion.
- Debe existir fallback/manual para casos de soporte, cuentas restringidas o clientes no listos para Embedded Signup, pero no debe ser el camino UX principal.

## Fuentes Consultadas

- Meta Postman API Network, Embedded Signup collection: https://www.postman.com/meta/whatsapp-business-platform/documentation/du6gzjv/embedded-signup
- Mirror de documentacion Meta, Embedded Signup: https://support.chatarchitect.com/books/meta-whatsapp/page/embedded-signup-developer-documentation
- Mirror de documentacion Meta, permisos WhatsApp: https://support.chatarchitect.com/books/meta-whatsapp/page/permissions-developer-documentation
- Mirror de documentacion Meta, Embedded Signup v4: https://support.chatarchitect.com/books/meta-whatsapp/page/version-4-developer-documentation

