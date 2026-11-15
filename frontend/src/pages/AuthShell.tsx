import { CalendarCheck, ShieldCheck, TrendingUp } from "lucide-react";
import type { ReactNode } from "react";

import { Logo } from "../components/Logo";

const POINTS = [
  { icon: CalendarCheck, title: "Cero dobles reservas", text: "La base de datos rechaza cualquier reserva que se cruce, incluso con peticiones simultáneas." },
  { icon: ShieldCheck, title: "Los datos de tu agencia, solo tuyos", text: "Aislamiento por agencia con Row Level Security en PostgreSQL." },
  { icon: TrendingUp, title: "Tu negocio de un vistazo", text: "Ocupación, ingresos del mes, entregas y devoluciones pendientes." },
];

/** Pantalla dividida para login y registro: propuesta de valor a la izquierda, formulario a la derecha. */
export function AuthShell({ title, subtitle, children }: { title: string; subtitle: string; children: ReactNode }) {
  return (
    <div className="grid min-h-dvh lg:grid-cols-[1.05fr_1fr]">
      <section className="relative hidden overflow-hidden bg-brand-900 p-12 text-white lg:flex lg:flex-col lg:justify-between">
        <div aria-hidden className="absolute -top-32 -right-32 size-96 rounded-full bg-brand-700/40 blur-3xl" />
        <div aria-hidden className="absolute -bottom-40 -left-20 size-[28rem] rounded-full bg-blue-500/20 blur-3xl" />
        <div className="relative">
          <Logo inverted />
        </div>
        <div className="relative max-w-md">
          <h2 className="text-3xl leading-tight font-semibold tracking-tight">
            Gestiona tu agencia de alquiler sin hojas de cálculo ni sorpresas.
          </h2>
          <ul className="mt-10 space-y-6">
            {POINTS.map(({ icon: Icon, title: pointTitle, text }) => (
              <li key={pointTitle} className="flex gap-4">
                <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-white/10">
                  <Icon className="size-5 text-blue-200" aria-hidden />
                </div>
                <div>
                  <p className="font-medium">{pointTitle}</p>
                  <p className="mt-0.5 text-sm text-blue-200">{text}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
        <p className="relative text-xs text-blue-300">Proyecto de portafolio · FastAPI · PostgreSQL · React</p>
      </section>

      <section className="flex items-center justify-center px-4 py-12 sm:px-8">
        <div className="w-full max-w-sm">
          <div className="mb-8 lg:hidden">
            <Logo />
          </div>
          <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
          <p className="mt-1 text-sm text-muted">{subtitle}</p>
          <div className="mt-8">{children}</div>
        </div>
      </section>
    </div>
  );
}
