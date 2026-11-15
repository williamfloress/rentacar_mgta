import { zodResolver } from "@hookform/resolvers/zod";
import clsx from "clsx";
import { Car, Pencil, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { PAGE_SIZE, useDeleteVehicle, useSaveVehicle, useVehicles } from "../api/hooks";
import { useAuth } from "../auth/AuthProvider";
import { useToast } from "../components/Toaster";
import {
  Badge,
  Button,
  Card,
  ConfirmDialog,
  EmptyState,
  ErrorState,
  Field,
  Input,
  Modal,
  PageHeader,
  Pagination,
  SearchInput,
  Select,
  Spinner,
  Table,
  Td,
  Th,
} from "../components/ui";
import { useDebounced } from "../lib/useDebounced";
import { errorMessage } from "../lib/errors";
import { vehicleStatusLabel } from "../lib/labels";
import { formatMoney, isValidMoney } from "../lib/money";
import type { Vehicle, VehicleStatus } from "../types";

const MAX_YEAR = new Date().getFullYear() + 1;

const schema = z.object({
  plate: z.string().trim().min(3, "Mínimo 3 caracteres").max(15),
  brand: z.string().trim().min(1, "Obligatorio").max(60),
  model: z.string().trim().min(1, "Obligatorio").max(60),
  color: z.string().trim().max(40),
  year: z
    .string()
    .regex(/^\d{4}$/, "Año de 4 cifras")
    .refine((y) => Number(y) >= 1950 && Number(y) <= MAX_YEAR, `Entre 1950 y ${MAX_YEAR}`),
  // El importe se mantiene como TEXTO hasta la API (que usa Decimal): nada de floats.
  daily_rate: z.string().trim().refine(isValidMoney, "Importe mayor que 0, con hasta 2 decimales (ej. 45.00)"),
  status: z.enum(["active", "maintenance", "retired"]),
});
type FormValues = z.infer<typeof schema>;

const STATUS_FILTERS: { value: VehicleStatus | ""; label: string }[] = [
  { value: "", label: "Todos" },
  { value: "active", label: "Operativos" },
  { value: "maintenance", label: "En taller" },
  { value: "retired", label: "De baja" },
];

function VehicleForm({ vehicle, onDone }: { vehicle: Vehicle | null; onDone: () => void }) {
  const toast = useToast();
  const save = useSaveVehicle();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: vehicle
      ? { ...vehicle, color: vehicle.color ?? "", year: String(vehicle.year) }
      : { plate: "", brand: "", model: "", color: "", year: String(MAX_YEAR - 1), daily_rate: "", status: "active" },
  });

  const onSubmit = handleSubmit((values) => {
    const data = { ...values, year: Number(values.year), color: values.color || null };
    save.mutate(
      { id: vehicle?.id, data: vehicle ? data : { ...data, status: undefined } },
      {
        onSuccess: (saved) => {
          toast.success(vehicle ? `Vehículo ${saved.plate} actualizado.` : `Vehículo ${saved.plate} añadido a la flota.`);
          onDone();
        },
        onError: (error) => toast.error(errorMessage(error)),
      },
    );
  });

  return (
    <form id="vehicle-form" onSubmit={onSubmit} className="grid gap-4 sm:grid-cols-2" noValidate>
      <Field label="Placa" error={errors.plate?.message}>
        {(a11y) => <Input {...a11y} className="font-mono uppercase" {...register("plate")} />}
      </Field>
      <Field label="Tarifa por día" error={errors.daily_rate?.message}>
        {(a11y) => <Input {...a11y} inputMode="decimal" placeholder="45.00" {...register("daily_rate")} />}
      </Field>
      <Field label="Marca" error={errors.brand?.message}>
        {(a11y) => <Input {...a11y} {...register("brand")} />}
      </Field>
      <Field label="Modelo" error={errors.model?.message}>
        {(a11y) => <Input {...a11y} {...register("model")} />}
      </Field>
      <Field label="Año" error={errors.year?.message}>
        {(a11y) => <Input {...a11y} inputMode="numeric" {...register("year")} />}
      </Field>
      <Field label="Color (opcional)" error={errors.color?.message}>
        {(a11y) => <Input {...a11y} {...register("color")} />}
      </Field>
      {vehicle && (
        <Field label="Estado" className="sm:col-span-2" hint="Un vehículo en taller o de baja no aparece como disponible para nuevas reservas.">
          {(a11y) => (
            <Select {...a11y} {...register("status")}>
              <option value="active">Operativo</option>
              <option value="maintenance">En taller</option>
              <option value="retired">De baja</option>
            </Select>
          )}
        </Field>
      )}
      <div className="flex justify-end gap-2 sm:col-span-2">
        <Button variant="secondary" onClick={onDone}>
          Cancelar
        </Button>
        <Button type="submit" loading={save.isPending}>
          {vehicle ? "Guardar cambios" : "Añadir vehículo"}
        </Button>
      </div>
    </form>
  );
}

export function VehiclesPage() {
  const { user, isOwner } = useAuth();
  const toast = useToast();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<VehicleStatus | "">("");
  const [offset, setOffset] = useState(0);
  const [editing, setEditing] = useState<Vehicle | "new" | null>(null);
  const [deleting, setDeleting] = useState<Vehicle | null>(null);
  const q = useDebounced(search.trim(), 300);
  const vehicles = useVehicles({ q, status, offset });
  const remove = useDeleteVehicle();
  const currency = user?.currency ?? "USD";

  const changeFilter = (apply: () => void) => {
    apply();
    setOffset(0);
  };

  const confirmDelete = () => {
    if (!deleting) return;
    remove.mutate(deleting.id, {
      onSuccess: () => toast.success(`Vehículo ${deleting.plate} eliminado.`),
      onError: (error) => toast.error(errorMessage(error)),
      onSettled: () => setDeleting(null),
    });
  };

  return (
    <>
      <PageHeader
        title="Flota"
        description="Los vehículos de tu agencia y su estado."
        actions={
          <Button icon={<Plus className="size-4" />} onClick={() => setEditing("new")}>
            Añadir vehículo
          </Button>
        }
      />

      <Card>
        <div className="flex flex-col gap-3 border-b border-line p-4 md:flex-row md:items-center md:justify-between">
          <div className="flex gap-1 overflow-x-auto rounded-lg bg-subtle p-1" role="tablist" aria-label="Filtrar por estado">
            {STATUS_FILTERS.map((filter) => (
              <button
                key={filter.value}
                type="button"
                role="tab"
                aria-selected={status === filter.value}
                onClick={() => changeFilter(() => setStatus(filter.value))}
                className={clsx(
                  "rounded-md px-3 py-1.5 text-sm font-medium whitespace-nowrap transition",
                  status === filter.value ? "bg-surface text-ink shadow-sm" : "text-muted hover:text-ink",
                )}
              >
                {filter.label}
              </button>
            ))}
          </div>
          <SearchInput
            value={search}
            onChange={(value) => changeFilter(() => setSearch(value))}
            placeholder="Buscar por placa, marca o modelo"
            className="md:w-80"
          />
        </div>

        {vehicles.isPending ? (
          <Spinner />
        ) : vehicles.isError ? (
          <ErrorState message={errorMessage(vehicles.error)} onRetry={() => vehicles.refetch()} />
        ) : vehicles.data.items.length === 0 ? (
          <EmptyState
            icon={<Car className="size-6" />}
            title={q || status ? "Ningún vehículo coincide" : "Aún no hay vehículos"}
            description={q || status ? "Prueba con otra búsqueda o filtro." : "Añade el primer vehículo de tu flota para empezar a alquilar."}
          />
        ) : (
          <>
            <Table>
              <thead>
                <tr>
                  <Th>Placa</Th>
                  <Th>Vehículo</Th>
                  <Th className="hidden md:table-cell">Color</Th>
                  <Th className="text-right">Tarifa / día</Th>
                  <Th>Estado</Th>
                  <Th>
                    <span className="sr-only">Acciones</span>
                  </Th>
                </tr>
              </thead>
              <tbody className={vehicles.isPlaceholderData ? "opacity-60" : undefined}>
                {vehicles.data.items.map((vehicle) => {
                  const badge = vehicleStatusLabel[vehicle.status];
                  return (
                    <tr key={vehicle.id} className="hover:bg-subtle/50">
                      <Td className="font-mono text-sm font-medium">{vehicle.plate}</Td>
                      <Td>
                        <p className="font-medium text-ink">
                          {vehicle.brand} {vehicle.model}
                        </p>
                        <p className="text-xs text-muted">{vehicle.year}</p>
                      </Td>
                      <Td className="hidden text-muted md:table-cell">{vehicle.color ?? "—"}</Td>
                      <Td className="text-right tabular-nums">{formatMoney(vehicle.daily_rate, currency)}</Td>
                      <Td>
                        <Badge tone={badge.tone}>{badge.label}</Badge>
                      </Td>
                      <Td className="text-right">
                        <div className="flex justify-end gap-1">
                          <Button variant="ghost" size="sm" onClick={() => setEditing(vehicle)} aria-label={`Editar ${vehicle.plate}`}>
                            <Pencil className="size-4" />
                          </Button>
                          {isOwner && (
                            <Button variant="ghost" size="sm" onClick={() => setDeleting(vehicle)} aria-label={`Eliminar ${vehicle.plate}`}>
                              <Trash2 className="size-4" />
                            </Button>
                          )}
                        </div>
                      </Td>
                    </tr>
                  );
                })}
              </tbody>
            </Table>
            <Pagination offset={offset} limit={PAGE_SIZE} total={vehicles.data.total} onChange={setOffset} />
          </>
        )}
      </Card>

      <Modal
        open={editing !== null}
        onClose={() => setEditing(null)}
        title={editing === "new" ? "Añadir vehículo" : `Editar ${editing?.plate ?? ""}`}
      >
        {editing !== null && <VehicleForm key={editing === "new" ? "new" : editing.id} vehicle={editing === "new" ? null : editing} onDone={() => setEditing(null)} />}
      </Modal>

      <ConfirmDialog
        open={deleting !== null}
        title="Eliminar vehículo"
        message={
          <>
            ¿Eliminar <b className="text-ink">{deleting?.plate}</b> de la flota? Si tiene historial de alquileres no se podrá
            borrar; en ese caso, cámbialo a <i>De baja</i>.
          </>
        }
        confirmLabel="Eliminar"
        tone="danger"
        loading={remove.isPending}
        onConfirm={confirmDelete}
        onClose={() => setDeleting(null)}
      />
    </>
  );
}
