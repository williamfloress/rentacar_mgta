import { useState } from "react";

import { useChangeRentalStatus } from "../api/hooks";
import { useAuth } from "../auth/AuthProvider";
import { daysBetween } from "../lib/dates";
import { errorMessage } from "../lib/errors";
import { formatMoney, toCents } from "../lib/money";
import type { Rental, RentalStatus } from "../types";
import { useToast } from "./Toaster";
import { Button, ConfirmDialog } from "./ui";

interface Action {
  target: RentalStatus;
  label: string;
  title: string;
  tone: "primary" | "danger";
}

const ACTIONS: Partial<Record<RentalStatus, Action[]>> = {
  reserved: [
    { target: "active", label: "Entregar", title: "Entregar vehículo", tone: "primary" },
    { target: "cancelled", label: "Cancelar", title: "Cancelar reserva", tone: "danger" },
  ],
  active: [{ target: "returned", label: "Recibir", title: "Registrar devolución", tone: "primary" }],
};

/** Botones para avanzar el ciclo de vida: Entregar / Cancelar / Recibir, con confirmación. */
export function RentalActions({ rental, today }: { rental: Rental; today: string }) {
  const { user } = useAuth();
  const toast = useToast();
  const change = useChangeRentalStatus();
  const [pending, setPending] = useState<Action | null>(null);
  const currency = user?.currency ?? "USD";

  const actions = (ACTIONS[rental.status] ?? []).filter(
    // No se puede entregar antes de la fecha reservada (regla del backend).
    (action) => action.target !== "active" || rental.start_date <= today,
  );
  if (actions.length === 0) return null;

  const description = () => {
    const car = `${rental.vehicle.brand} ${rental.vehicle.model} (${rental.vehicle.plate})`;
    if (pending?.target === "active") return <>Se entrega el {car} a <b className="text-ink">{rental.customer.full_name}</b>.</>;
    if (pending?.target === "cancelled") return <>La reserva del {car} se cancelará y el vehículo quedará libre en esas fechas.</>;
    const lateDays = daysBetween(rental.end_date, today);
    if (lateDays > 0) {
      // Estimación informativa; el importe definitivo lo calcula el servidor.
      const estimate = Math.round(toCents(rental.daily_rate_snapshot) * 1.5 * lateDays);
      return (
        <>
          El {car} vuelve con <b className="text-red-700">{lateDays} día(s) de retraso</b>. Se aplicará un recargo de
          aproximadamente <b className="text-ink">{formatMoney(estimate, currency)}</b>.
        </>
      );
    }
    return <>Se registra la devolución del {car}. El vehículo vuelve a estar disponible.</>;
  };

  const confirm = () => {
    if (!pending) return;
    change.mutate(
      { id: rental.id, status: pending.target },
      {
        onSuccess: (updated) => {
          const fee = toCents(updated.late_fee);
          toast.success(
            pending.target === "returned" && fee > 0
              ? `Devolución registrada con recargo de ${formatMoney(fee, currency)}.`
              : { active: "Vehículo entregado.", cancelled: "Reserva cancelada.", returned: "Devolución registrada.", reserved: "" }[pending.target],
          );
          setPending(null);
        },
        onError: (error) => {
          toast.error(errorMessage(error));
          setPending(null);
        },
      },
    );
  };

  return (
    <div className="flex justify-end gap-1.5">
      {actions.map((action) => (
        <Button key={action.target} size="sm" variant={action.tone === "danger" ? "ghost" : "secondary"} onClick={() => setPending(action)}>
          {action.label}
        </Button>
      ))}
      <ConfirmDialog
        open={pending !== null}
        title={pending?.title ?? ""}
        message={description()}
        confirmLabel={pending?.label ?? ""}
        tone={pending?.tone}
        loading={change.isPending}
        onConfirm={confirm}
        onClose={() => setPending(null)}
      />
    </div>
  );
}
