import clsx from "clsx";
import { CalendarPlus, ClipboardList } from "lucide-react";
import { useSearchParams } from "react-router";

import { PAGE_SIZE, useRentals } from "../api/hooks";
import { useAuth } from "../auth/AuthProvider";
import { RentalActions } from "../components/RentalActions";
import {
  Badge,
  Card,
  EmptyState,
  ErrorState,
  LinkButton,
  PageHeader,
  Pagination,
  SearchInput,
  Spinner,
  Table,
  Td,
  Th,
} from "../components/ui";
import { daysBetween, formatDate, todayISO } from "../lib/dates";
import { errorMessage } from "../lib/errors";
import { rentalBadge } from "../lib/labels";
import { formatMoney, toCents } from "../lib/money";
import { useDebounced } from "../lib/useDebounced";
import type { RentalStatus } from "../types";

const STATUS_FILTERS: { value: RentalStatus | ""; label: string }[] = [
  { value: "", label: "Todos" },
  { value: "reserved", label: "Reservados" },
  { value: "active", label: "En curso" },
  { value: "returned", label: "Devueltos" },
  { value: "cancelled", label: "Cancelados" },
];

export function RentalsPage() {
  const { user } = useAuth();
  // Filtros en la URL: se pueden compartir, recargar y usar "atrás" del navegador.
  const [params, setParams] = useSearchParams();
  const search = params.get("q") ?? "";
  const status = (params.get("status") ?? "") as RentalStatus | "";
  const offset = Number(params.get("offset") ?? 0);
  const q = useDebounced(search.trim(), 300);
  const rentals = useRentals({ q, status, offset });
  const today = todayISO();
  const currency = user?.currency ?? "USD";

  const update = (changes: Record<string, string>) => {
    const next = new URLSearchParams(params);
    for (const [key, value] of Object.entries(changes)) {
      if (value) next.set(key, value);
      else next.delete(key);
    }
    if (!("offset" in changes)) next.delete("offset");
    setParams(next, { replace: true });
  };

  return (
    <>
      <PageHeader
        title="Alquileres"
        description="Reservas, vehículos en la calle e historial."
        actions={
          <LinkButton to="/rentals/new" icon={<CalendarPlus className="size-4" />}>
            Nuevo alquiler
          </LinkButton>
        }
      />

      <Card>
        <div className="flex flex-col gap-3 border-b border-line p-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex gap-1 overflow-x-auto rounded-lg bg-subtle p-1" role="tablist" aria-label="Filtrar por estado">
            {STATUS_FILTERS.map((filter) => (
              <button
                key={filter.value}
                type="button"
                role="tab"
                aria-selected={status === filter.value}
                onClick={() => update({ status: filter.value })}
                className={clsx(
                  "rounded-md px-3 py-1.5 text-sm font-medium whitespace-nowrap transition",
                  status === filter.value ? "bg-surface text-ink shadow-sm" : "text-muted hover:text-ink",
                )}
              >
                {filter.label}
              </button>
            ))}
          </div>
          <SearchInput value={search} onChange={(value) => update({ q: value })} placeholder="Buscar por placa, cliente o documento" className="lg:w-80" />
        </div>

        {rentals.isPending ? (
          <Spinner />
        ) : rentals.isError ? (
          <ErrorState message={errorMessage(rentals.error)} onRetry={() => rentals.refetch()} />
        ) : rentals.data.items.length === 0 ? (
          <EmptyState
            icon={<ClipboardList className="size-6" />}
            title={q || status ? "Ningún alquiler coincide" : "Aún no hay alquileres"}
            description={q || status ? "Prueba con otra búsqueda o filtro." : "Crea el primero desde «Nuevo alquiler»."}
          />
        ) : (
          <>
            <Table>
              <thead>
                <tr>
                  <Th>Vehículo</Th>
                  <Th>Cliente</Th>
                  <Th>Fechas</Th>
                  <Th className="text-right">Importe</Th>
                  <Th>Estado</Th>
                  <Th>
                    <span className="sr-only">Acciones</span>
                  </Th>
                </tr>
              </thead>
              <tbody className={rentals.isPlaceholderData ? "opacity-60" : undefined}>
                {rentals.data.items.map((rental) => {
                  const badge = rentalBadge(rental, today);
                  const fee = toCents(rental.late_fee);
                  const days = daysBetween(rental.start_date, rental.end_date);
                  return (
                    <tr key={rental.id} className="hover:bg-subtle/50">
                      <Td>
                        <p className="font-medium text-ink">
                          {rental.vehicle.brand} {rental.vehicle.model}
                        </p>
                        <p className="font-mono text-xs text-muted">{rental.vehicle.plate}</p>
                      </Td>
                      <Td>
                        <p className="text-ink">{rental.customer.full_name}</p>
                        <p className="font-mono text-xs text-muted">{rental.customer.document_id}</p>
                      </Td>
                      <Td className="whitespace-nowrap">
                        <p className="text-ink">
                          {formatDate(rental.start_date)} → {formatDate(rental.end_date)}
                        </p>
                        <p className="text-xs text-muted">
                          {days} {days === 1 ? "día" : "días"}
                        </p>
                      </Td>
                      <Td className="text-right whitespace-nowrap tabular-nums">
                        <p className="text-ink">{formatMoney(toCents(rental.total_amount) + fee, currency)}</p>
                        {fee > 0 && <p className="text-xs text-red-700">incl. {formatMoney(fee, currency)} recargo</p>}
                      </Td>
                      <Td>
                        <Badge tone={badge.tone}>{badge.label}</Badge>
                      </Td>
                      <Td>
                        <RentalActions rental={rental} today={today} />
                      </Td>
                    </tr>
                  );
                })}
              </tbody>
            </Table>
            <Pagination offset={offset} limit={PAGE_SIZE} total={rentals.data.total} onChange={(next) => update({ offset: String(next) })} />
          </>
        )}
      </Card>
    </>
  );
}
