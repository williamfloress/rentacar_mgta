import { AlertTriangle, CalendarClock, CalendarPlus, Car, DollarSign, KeyRound } from "lucide-react";
import type { ReactNode } from "react";

import { useAgenda, useDashboard, useRevenue } from "../api/hooks";
import { useAuth } from "../auth/AuthProvider";
import { RentalActions } from "../components/RentalActions";
import { RevenueChart } from "../components/RevenueChart";
import { Badge, Card, EmptyState, ErrorState, LinkButton, PageHeader, Spinner } from "../components/ui";
import { formatShortDate, relativeDay } from "../lib/dates";
import { errorMessage } from "../lib/errors";
import { isOverdue } from "../lib/labels";
import { formatMoney } from "../lib/money";
import type { Rental } from "../types";

function StatTile({ label, value, detail, icon }: { label: string; value: ReactNode; detail?: ReactNode; icon: ReactNode }) {
  return (
    <Card className="p-5">
      <div className="flex items-start justify-between">
        <p className="text-sm font-medium text-muted">{label}</p>
        <span className="rounded-lg bg-brand-50 p-2 text-brand-700">{icon}</span>
      </div>
      <p className="mt-2 text-3xl font-semibold tracking-tight text-ink tabular-nums">{value}</p>
      {detail && <div className="mt-1 text-sm text-muted">{detail}</div>}
    </Card>
  );
}

function AgendaList({
  title,
  icon,
  rentals,
  today,
  dateOf,
  empty,
}: {
  title: string;
  icon: ReactNode;
  rentals: Rental[];
  today: string;
  dateOf: (r: Rental) => string;
  empty: string;
}) {
  return (
    <Card>
      <div className="flex items-center gap-2 border-b border-line px-5 py-3.5">
        <span className="text-muted">{icon}</span>
        <h2 className="font-semibold">{title}</h2>
        <span className="ml-auto text-sm text-muted">{rentals.length}</span>
      </div>
      {rentals.length === 0 ? (
        <p className="px-5 py-10 text-center text-sm text-muted">{empty}</p>
      ) : (
        <ul className="divide-y divide-line">
          {rentals.map((rental) => {
            const date = dateOf(rental);
            const late = isOverdue(rental, today);
            return (
              <li key={rental.id} className="flex flex-wrap items-center gap-x-4 gap-y-2 px-5 py-3">
                <div className="w-16 shrink-0 text-center">
                  <p className="text-sm font-semibold text-ink capitalize">{formatShortDate(date)}</p>
                  <p className={late ? "text-xs font-medium text-red-600" : "text-xs text-muted"}>{relativeDay(date, today)}</p>
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-ink">
                    {rental.vehicle.brand} {rental.vehicle.model}{" "}
                    <span className="font-mono text-xs text-muted">{rental.vehicle.plate}</span>
                  </p>
                  <p className="truncate text-sm text-muted">{rental.customer.full_name}</p>
                </div>
                {late && <Badge tone="red">Atrasado</Badge>}
                <RentalActions rental={rental} today={today} />
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}

export function DashboardPage() {
  const { user } = useAuth();
  const summary = useDashboard();
  const agenda = useAgenda();
  const revenue = useRevenue(6);
  const currency = user?.currency ?? "USD";

  if (summary.isPending || agenda.isPending) return <Spinner />;
  if (summary.isError) return <ErrorState message={errorMessage(summary.error)} onRetry={() => summary.refetch()} />;
  if (agenda.isError) return <ErrorState message={errorMessage(agenda.error)} onRetry={() => agenda.refetch()} />;

  const s = summary.data;
  const firstName = user?.full_name.split(" ")[0] ?? "";
  const isEmpty = s.vehicles_total === 0;

  return (
    <>
      <PageHeader
        title={`Hola, ${firstName}`}
        description="Esto es lo que pasa hoy en tu agencia."
        actions={
          <LinkButton to="/rentals/new" icon={<CalendarPlus className="size-4" />}>
            Nuevo alquiler
          </LinkButton>
        }
      />

      {isEmpty ? (
        <Card>
          <EmptyState
            icon={<Car className="size-6" />}
            title="Empieza registrando tu flota"
            description="Cuando tengas vehículos y clientes podrás crear alquileres y verás aquí tus métricas."
            action={
<LinkButton to="/vehicles">Añadir vehículos</LinkButton>
            }
          />
        </Card>
      ) : (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatTile
              label="Disponibles hoy"
              icon={<Car className="size-4" />}
              value={
                <>
                  {s.vehicles_available_today}
                  <span className="text-lg font-normal text-muted"> / {s.vehicles_total}</span>
                </>
              }
              detail="vehículos libres para salir"
            />
            <StatTile
              label="En curso"
              icon={<KeyRound className="size-4" />}
              value={s.rentals_active}
              detail={
                s.rentals_overdue > 0 ? (
                  <span className="inline-flex items-center gap-1 font-medium text-red-700">
                    <AlertTriangle className="size-3.5" aria-hidden /> {s.rentals_overdue} con devolución atrasada
                  </span>
                ) : (
                  "ninguno atrasado"
                )
              }
            />
            <StatTile label="Reservas pendientes" icon={<CalendarClock className="size-4" />} value={s.rentals_reserved} detail="por entregar" />
            <StatTile
              label="Ingresos del mes"
              icon={<DollarSign className="size-4" />}
              value={formatMoney(s.revenue_current_month, currency)}
              detail="alquileres que ya salieron"
            />
          </div>

          <div className="grid gap-6 xl:grid-cols-2">
            <AgendaList
              title="Próximas entregas"
              icon={<CalendarClock className="size-4" />}
              rentals={agenda.data.pickups}
              today={agenda.data.today}
              dateOf={(r) => r.start_date}
              empty="No hay entregas en los próximos 7 días."
            />
            <AgendaList
              title="Devoluciones pendientes"
              icon={<KeyRound className="size-4" />}
              rentals={agenda.data.returns}
              today={agenda.data.today}
              dateOf={(r) => r.end_date}
              empty="No hay vehículos fuera ahora mismo."
            />
          </div>

          <Card className="p-5">
            <div className="mb-6">
              <h2 className="font-semibold">Ingresos por mes</h2>
              <p className="text-sm text-muted">Total más recargos, por mes de inicio del alquiler.</p>
            </div>
            {revenue.isPending ? (
              <Spinner />
            ) : revenue.isError ? (
              <ErrorState message={errorMessage(revenue.error)} />
            ) : (
              <RevenueChart data={revenue.data} currency={currency} />
            )}
          </Card>
        </div>
      )}
    </>
  );
}
