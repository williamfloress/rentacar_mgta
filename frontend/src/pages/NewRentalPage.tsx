import clsx from "clsx";
import { ArrowLeft, Car, CircleCheck, UserPlus, Users } from "lucide-react";
import { useState, type ReactNode } from "react";
import { useNavigate } from "react-router";

import { useAvailableVehicles, useCreateRental, useCustomers } from "../api/hooks";
import { useAuth } from "../auth/AuthProvider";
import { useToast } from "../components/Toaster";
import { Button, Card, EmptyState, ErrorState, Field, Input, LinkButton, Modal, SearchInput, Spinner, Textarea } from "../components/ui";
import { ApiError } from "../lib/api";
import { addDays, daysBetween, formatDate, todayISO } from "../lib/dates";
import { errorMessage } from "../lib/errors";
import { formatMoney, toCents } from "../lib/money";
import { useDebounced } from "../lib/useDebounced";
import type { Customer, Vehicle } from "../types";
import { CustomerForm } from "./CustomerForm";

function Step({ number, title, done, children }: { number: number; title: string; done: boolean; children: ReactNode }) {
  return (
    <Card className="p-5">
      <div className="mb-4 flex items-center gap-3">
        <span
          className={clsx(
            "flex size-7 items-center justify-center rounded-full text-sm font-semibold",
            done ? "bg-emerald-600 text-white" : "bg-brand-50 text-brand-700",
          )}
          aria-hidden
        >
          {done ? <CircleCheck className="size-4" /> : number}
        </span>
        <h2 className="font-semibold">{title}</h2>
      </div>
      {children}
    </Card>
  );
}

export function NewRentalPage() {
  const { user } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const today = todayISO();
  const currency = user?.currency ?? "USD";

  const [start, setStart] = useState(today);
  const [end, setEnd] = useState(addDays(today, 3));
  const [vehicle, setVehicle] = useState<Vehicle | null>(null);
  const [customer, setCustomer] = useState<Customer | null>(null);
  const [customerSearch, setCustomerSearch] = useState("");
  const [creatingCustomer, setCreatingCustomer] = useState(false);
  const [notes, setNotes] = useState("");

  const days = daysBetween(start, end);
  const datesValid = start >= today && days > 0;
  const available = useAvailableVehicles(start, end, datesValid);
  const customerQuery = useDebounced(customerSearch.trim(), 250);
  const customers = useCustomers({ q: customerQuery, limit: 6 });
  const create = useCreateRental();

  // Si cambian las fechas y el vehículo elegido deja de estar libre, se deselecciona.
  const vehicleStillFree = !vehicle || !available.data || available.data.some((v) => v.id === vehicle.id);
  const selectedVehicle = vehicleStillFree ? vehicle : null;

  const totalCents = selectedVehicle && datesValid ? toCents(selectedVehicle.daily_rate) * days : null;
  const canSubmit = datesValid && selectedVehicle && customer && !create.isPending;

  const submit = () => {
    if (!selectedVehicle || !customer) return;
    create.mutate(
      { vehicle_id: selectedVehicle.id, customer_id: customer.id, start_date: start, end_date: end, notes: notes.trim() || undefined },
      {
        onSuccess: (rental) => {
          toast.success(`Reserva creada: ${rental.vehicle.plate} para ${rental.customer.full_name}.`);
          navigate("/rentals");
        },
        onError: (error) => {
          toast.error(errorMessage(error));
          // 409: alguien reservó ese carro mientras tanto. Se refresca la lista.
          if (error instanceof ApiError && error.status === 409) {
            setVehicle(null);
            void available.refetch();
          }
        },
      },
    );
  };

  return (
    <>
      <div className="mb-6">
        <LinkButton to="/rentals" variant="ghost" size="sm" icon={<ArrowLeft className="size-4" />} className="-ml-3 mb-2">
          Alquileres
        </LinkButton>
        <h1 className="text-2xl font-semibold tracking-tight">Nuevo alquiler</h1>
        <p className="mt-1 text-sm text-muted">Elige las fechas y verás solo los vehículos libres en todo ese periodo.</p>
      </div>

      <div className="grid items-start gap-6 lg:grid-cols-[1fr_20rem]">
        <div className="space-y-6">
          <Step number={1} title="Fechas" done={datesValid}>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Recogida" error={start < today ? "No puede ser en el pasado" : undefined}>
                {(a11y) => (
                  <Input
                    {...a11y}
                    type="date"
                    min={today}
                    value={start}
                    onChange={(e) => {
                      const value = e.target.value;
                      setStart(value);
                      if (value && end <= value) setEnd(addDays(value, 1));
                    }}
                  />
                )}
              </Field>
              <Field
                label="Devolución"
                error={days <= 0 ? "Debe ser posterior a la recogida" : undefined}
                hint={days > 0 ? `${days} ${days === 1 ? "día" : "días"} (el día de devolución no se cobra)` : undefined}
              >
                {(a11y) => <Input {...a11y} type="date" min={addDays(start, 1)} value={end} onChange={(e) => setEnd(e.target.value)} />}
              </Field>
            </div>
          </Step>

          <Step number={2} title="Vehículo disponible" done={Boolean(selectedVehicle)}>
            {!datesValid ? (
              <p className="text-sm text-muted">Corrige las fechas para ver la disponibilidad.</p>
            ) : available.isPending ? (
              <Spinner label="Buscando vehículos libres…" />
            ) : available.isError ? (
              <ErrorState message={errorMessage(available.error)} onRetry={() => available.refetch()} />
            ) : available.data.length === 0 ? (
              <EmptyState icon={<Car className="size-6" />} title="No hay vehículos libres en esas fechas" description="Prueba a mover las fechas." />
            ) : (
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3" role="radiogroup" aria-label="Vehículos disponibles">
                {available.data.map((option) => {
                  const selected = selectedVehicle?.id === option.id;
                  return (
                    <button
                      key={option.id}
                      type="button"
                      role="radio"
                      aria-checked={selected}
                      onClick={() => setVehicle(option)}
                      className={clsx(
                        "rounded-xl border p-4 text-left transition",
                        selected ? "border-brand-600 bg-brand-50 ring-2 ring-brand-600/20" : "border-line hover:border-brand-500/50 hover:bg-subtle/50",
                      )}
                    >
                      <p className="font-medium text-ink">
                        {option.brand} {option.model}
                      </p>
                      <p className="mt-0.5 text-xs text-muted">
                        <span className="font-mono">{option.plate}</span> · {option.year}
                        {option.color && ` · ${option.color}`}
                      </p>
                      <p className="mt-3 text-sm">
                        <span className="font-semibold text-ink tabular-nums">{formatMoney(option.daily_rate, currency)}</span>
                        <span className="text-muted"> / día</span>
                      </p>
                    </button>
                  );
                })}
              </div>
            )}
          </Step>

          <Step number={3} title="Cliente" done={Boolean(customer)}>
            {customer ? (
              <div className="flex items-center justify-between gap-4 rounded-xl border border-brand-600 bg-brand-50 p-4">
                <div>
                  <p className="font-medium text-ink">{customer.full_name}</p>
                  <p className="font-mono text-xs text-muted">{customer.document_id}</p>
                </div>
                <Button variant="secondary" size="sm" onClick={() => setCustomer(null)}>
                  Cambiar
                </Button>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="flex flex-col gap-2 sm:flex-row">
                  <SearchInput value={customerSearch} onChange={setCustomerSearch} placeholder="Buscar cliente por nombre o documento" className="flex-1" />
                  <Button variant="secondary" icon={<UserPlus className="size-4" />} onClick={() => setCreatingCustomer(true)}>
                    Nuevo cliente
                  </Button>
                </div>
                {customers.isPending ? (
                  <Spinner />
                ) : customers.isError ? (
                  <ErrorState message={errorMessage(customers.error)} />
                ) : customers.data.items.length === 0 ? (
                  <EmptyState icon={<Users className="size-6" />} title="Sin resultados" description="Registra al cliente con «Nuevo cliente»." />
                ) : (
                  <ul className="divide-y divide-line rounded-xl border border-line">
                    {customers.data.items.map((option) => (
                      <li key={option.id}>
                        <button type="button" onClick={() => setCustomer(option)} className="flex w-full items-center justify-between px-4 py-2.5 text-left hover:bg-subtle/60">
                          <span className="text-sm font-medium text-ink">{option.full_name}</span>
                          <span className="font-mono text-xs text-muted">{option.document_id}</span>
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </Step>
        </div>

        {/* Resumen: fijo a la vista en escritorio */}
        <Card className="p-5 lg:sticky lg:top-8">
          <h2 className="font-semibold">Resumen</h2>
          <dl className="mt-4 space-y-3 text-sm">
            <div className="flex justify-between gap-4">
              <dt className="text-muted">Periodo</dt>
              <dd className="text-right text-ink">{datesValid ? `${formatDate(start)} → ${formatDate(end)}` : "—"}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-muted">Vehículo</dt>
              <dd className="text-right text-ink">{selectedVehicle ? `${selectedVehicle.brand} ${selectedVehicle.model}` : "—"}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-muted">Cliente</dt>
              <dd className="text-right text-ink">{customer?.full_name ?? "—"}</dd>
            </div>
            {selectedVehicle && datesValid && (
              <div className="flex justify-between gap-4">
                <dt className="text-muted">Tarifa</dt>
                <dd className="text-right text-ink tabular-nums">
                  {formatMoney(selectedVehicle.daily_rate, currency)} × {days} {days === 1 ? "día" : "días"}
                </dd>
              </div>
            )}
          </dl>
          <div className="mt-4 flex items-baseline justify-between border-t border-line pt-4">
            <span className="text-sm font-medium text-muted">Total</span>
            <span className="text-2xl font-semibold tracking-tight tabular-nums">{totalCents !== null ? formatMoney(totalCents, currency) : "—"}</span>
          </div>
          <Field label="Notas (opcional)" className="mt-5">
            {(a11y) => <Textarea {...a11y} rows={2} maxLength={500} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Ej.: entrega en el aeropuerto" />}
          </Field>
          <Button className="mt-5 w-full" disabled={!canSubmit} loading={create.isPending} onClick={submit}>
            Confirmar reserva
          </Button>
          <p className="mt-3 text-center text-xs text-muted">Se registra como reserva; el vehículo se entrega desde la agenda.</p>
        </Card>
      </div>

      <Modal open={creatingCustomer} onClose={() => setCreatingCustomer(false)} title="Nuevo cliente">
        {creatingCustomer && (
          <CustomerForm
            customer={null}
            onDone={(saved) => {
              if (saved) setCustomer(saved);
              setCreatingCustomer(false);
            }}
          />
        )}
      </Modal>
    </>
  );
}
