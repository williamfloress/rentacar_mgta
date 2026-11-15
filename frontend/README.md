# Frontend · rent-a-CAR

Panel web de la agencia: React 19 + TypeScript (estricto) + Vite + Tailwind CSS v4.

```bash
npm install
cp .env.example .env      # VITE_API_URL=http://localhost:8000
npm run dev               # http://localhost:5173
```

| Script | Qué hace |
|---|---|
| `npm run dev` | Servidor de desarrollo con recarga en caliente |
| `npm test` | Pruebas (Vitest + Testing Library) |
| `npm run lint` / `npm run typecheck` | ESLint / TypeScript |
| `npm run build` | Compilación de producción en `dist/` |

## Organización

```
src/
├── pages/          una pantalla por archivo (Dashboard, NewRental, Rentals, Vehicles, Customers, Team, Login…)
├── components/     piezas reutilizables: ui.tsx (sistema de diseño), AppLayout, RevenueChart, RentalActions
├── api/hooks.ts    acceso a datos con TanStack Query (caché e invalidación tras cada cambio)
├── auth/           sesión (token, perfil, login/logout)
└── lib/            cliente HTTP, dinero en céntimos, fechas sin desfase horario, traducción de errores
```

## Decisiones

- **Dinero**: la API envía importes como texto (`"200.00"`). Se calculan en céntimos enteros
  (`lib/money.ts`) y solo se formatean al mostrarlos. Nunca `parseFloat` para sumar.
- **Fechas**: `new Date("2026-11-14")` es medianoche UTC y en Venezuela se ve como el día 13.
  `lib/dates.ts` construye siempre fechas locales.
- **Errores**: la API responde en inglés (para desarrolladores); `lib/errors.ts` los traduce
  a mensajes claros para el usuario.
- **Filtros en la URL** (página de alquileres): se pueden compartir y recargar.
- **Arranque en frío**: si el login tarda más de 4 s, se avisa de que el servidor gratuito está despertando.
