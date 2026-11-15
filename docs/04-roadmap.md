# 04 · Roadmap

Orden sugerido. Cada fase termina con algo que se puede enseñar.

## Fase 0 · Dejar el backend funcionando ✅

Completada: todo se ejecutó contra PostgreSQL real; la primera ejecución no destapó fallos de
cableado, solo un detalle de formato (`"0"` en lugar de `"0.00"` en los ingresos).

- [x] `docker compose up --build` y recorrer el flujo de prueba del README en `/docs`.
- [x] Corregir lo que aparezca (es normal que salgan ajustes pequeños).
- [x] `pip freeze > backend/requirements.lock` y usarlo en el Dockerfile para builds reproducibles.
- [x] **Pruebas de integración** de la API con `TestClient` contra PostgreSQL real. Las más
      valiosas: (1) dos reservas solapadas → una recibe 409; (2) un usuario de la agencia B
      recibe 404 al pedir un recurso de A; (3) un agente recibe 403 al borrar; (4) un token
      de un usuario desactivado deja de funcionar.
- [x] **CI con GitHub Actions**: levantar un servicio PostgreSQL, ejecutar `scripts/test_schema.sh`
      y `pytest` en cada *push*. Un *badge* verde en el README impresiona más que cualquier frase.

## Fase 1 · Completar el MVP ✅ (salvo el contrato PDF)

- [x] **Frontend** (React + TypeScript + Vite): login, flota, clientes, nuevo alquiler con
      búsqueda de disponibilidad, lista de alquileres y dashboard. Ver `frontend/README.md`.
- [x] **Limitación de intentos de login** (*rate limiting*), p. ej. con `slowapi`. Un contador
      en memoria no sirve si hay varias instancias; para el MVP de una sola instancia basta.
- [ ] **Contrato en PDF** generado al activar un alquiler.
- [x] Revisar reservas futuras al poner un vehículo en `maintenance` (ahora: 409 si tiene reservas pendientes).
- [x] Paginación con total de resultados (`X-Total-Count`) para las tablas del frontend.
- [x] Datos de ejemplo (*seed*) para que el demo público no esté vacío.

## Fase 2 · Pulir para el portafolio

- [ ] README en inglés (o versión bilingüe): los reclutadores remotos suelen leer en inglés.
- [x] Capturas en el README. *(Pendiente: GIF corto del flujo principal.)*
- [x] Sección "Decisiones técnicas" resumida (sale de `docs/01`).
- [ ] Nota de seguridad: qué cubre del OWASP Top 10 y qué queda fuera.
- [ ] Demo pública con credenciales de prueba.

## Fase 3 · Producto (solo si hay interés real)

Antes de construir nada de esto, **habla con 2 o 3 dueños de agencias pequeñas**. Lo que
más separa un proyecto de portafolio de un producto no es el código, sino saber si alguien
lo necesita y qué pagaría.

- [ ] Recordatorios y confirmaciones por WhatsApp o email.
- [ ] Fotos de inspección al entregar y recibir (daños, kilometraje, combustible).
- [ ] Mantenimientos programados y calendario tipo Gantt por vehículo.
- [ ] Varias monedas y tarifas por temporada.
- [ ] Cierre de sesión en servidor y *refresh tokens*; recuperación de contraseña.
- [ ] Plan de suscripción por agencia.

## Fase 4 · Datos (tu diferencial)

- [ ] Analítica de ocupación e ingresos por vehículo y por temporada.
- [ ] Predicción de demanda con Python, usando el historial de alquileres. Se integra como un
      módulo más del mismo backend y conecta el proyecto con tu interés en datos.

## Deuda técnica conocida

| Tema | Detalle |
|---|---|
| Migraciones al arrancar | Válido con una instancia; con varias, moverlas a un paso de despliegue aparte. |
| Consulta de usuario por petición | Simple y segura; si hace falta rendimiento, cachear con invalidación. |
| SQLAlchemy síncrono | Suficiente para este volumen; revisar si crece la concurrencia. |
| `updated_at` en el ORM | Lo mantiene un trigger de la BD; el objeto en memoria puede quedar desactualizado hasta recargarlo. |
| Devolución vencida | Un carro con la devolución atrasada se bloquea en la aplicación (`app/availability.py`), no en la BD: depende de "hoy" y no cabe en una restricción. Ventana de carrera teórica, documentada. |
| Rate limiting en memoria | Correcto con una instancia; con varias, moverlo a Redis. |
| Token en localStorage | Expuesto ante un XSS. Alternativa: cookie httpOnly + protección CSRF (requiere mismo dominio para API y panel). |
| "Hoy" en el navegador | El panel calcula "hoy" con la hora del navegador y la API con `TIMEZONE`; coinciden si el usuario está en la zona de la agencia. |
| Bundle del frontend sin dividir | ~150 KB gzip; dividir por rutas (`lazy`) si crece. |
| Reglas de negocio supuestas | Ver el apartado 3 de `docs/01-arquitectura-y-decisiones.md`. |
