import type { Rental, RentalStatus, VehicleStatus } from "../types";

export type Tone = "neutral" | "blue" | "green" | "amber" | "red" | "violet";

export const vehicleStatusLabel: Record<VehicleStatus, { label: string; tone: Tone }> = {
  active: { label: "Operativo", tone: "green" },
  maintenance: { label: "En taller", tone: "amber" },
  retired: { label: "De baja", tone: "neutral" },
};

export const rentalStatusLabel: Record<RentalStatus, { label: string; tone: Tone }> = {
  reserved: { label: "Reservado", tone: "blue" },
  active: { label: "En curso", tone: "violet" },
  returned: { label: "Devuelto", tone: "green" },
  cancelled: { label: "Cancelado", tone: "neutral" },
};

/** En curso y con la fecha de devolución ya vencida. */
export function isOverdue(rental: Pick<Rental, "status" | "end_date">, today: string): boolean {
  return rental.status === "active" && rental.end_date < today;
}

export function rentalBadge(rental: Rental, today: string): { label: string; tone: Tone } {
  return isOverdue(rental, today) ? { label: "Atrasado", tone: "red" } : rentalStatusLabel[rental.status];
}
