/**
 * Fechas de calendario ("2026-11-14") sin sorpresas de zona horaria.
 *
 * Trampa clásica: new Date("2026-11-14") se interpreta como medianoche UTC, y
 * en Venezuela (UTC-4) eso se muestra como el 13 de noviembre. Aquí las fechas
 * se construyen SIEMPRE en hora local a partir de año, mes y día.
 */
import type { ISODate } from "../types";

const MS_PER_DAY = 24 * 60 * 60 * 1000;

export function parseISODate(value: ISODate): Date {
  const [year, month, day] = value.split("-").map(Number);
  if (!year || !month || !day) throw new Error(`Invalid date: "${value}"`);
  return new Date(year, month - 1, day);
}

export function toISODate(date: Date): ISODate {
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${date.getFullYear()}-${month}-${day}`;
}

export function todayISO(now: Date = new Date()): ISODate {
  return toISODate(now);
}

export function addDays(value: ISODate, days: number): ISODate {
  const date = parseISODate(value);
  date.setDate(date.getDate() + days);
  return toISODate(date);
}

/** Días cobrados de un rango semiabierto [inicio, fin): del 10 al 15 son 5. */
export function daysBetween(start: ISODate, end: ISODate): number {
  // Math.round absorbe los cambios de horario de verano (días de 23 o 25 horas).
  return Math.round((parseISODate(end).getTime() - parseISODate(start).getTime()) / MS_PER_DAY);
}

const dayFormatter = new Intl.DateTimeFormat("es-VE", { day: "numeric", month: "short", year: "numeric" });
const shortFormatter = new Intl.DateTimeFormat("es-VE", { day: "numeric", month: "short" });
const monthFormatter = new Intl.DateTimeFormat("es-VE", { month: "short" });

export function formatDate(value: ISODate): string {
  return dayFormatter.format(parseISODate(value));
}

export function formatShortDate(value: ISODate): string {
  return shortFormatter.format(parseISODate(value));
}

export function formatMonth(value: ISODate): string {
  return monthFormatter.format(parseISODate(value)).replace(".", "");
}

/** "hoy", "mañana", "en 3 días", "hace 2 días". */
export function relativeDay(value: ISODate, today: ISODate): string {
  const diff = daysBetween(today, value);
  if (diff === 0) return "hoy";
  if (diff === 1) return "mañana";
  if (diff === -1) return "ayer";
  return diff > 0 ? `en ${diff} días` : `hace ${-diff} días`;
}
