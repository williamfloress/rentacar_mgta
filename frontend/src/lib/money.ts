/**
 * Dinero sin errores de coma flotante.
 *
 * La API envía importes como texto ("40.00"). Para CALCULAR se convierten a
 * céntimos enteros (4000): 0.1 + 0.2 con float da 0.30000000000000004, con
 * enteros no. Solo al MOSTRAR se divide entre 100 y se formatea.
 */
import type { Money } from "../types";

const MONEY_PATTERN = /^(-)?(\d+)(?:\.(\d{1,2}))?$/;

/** "40.5" → 4050. Lanza error si el texto no es un importe válido. */
export function toCents(value: Money): number {
  const match = MONEY_PATTERN.exec(value.trim());
  if (!match) throw new Error(`Invalid money amount: "${value}"`);
  const [, sign, units = "0", decimals = ""] = match;
  const cents = Number(units) * 100 + Number(decimals.padEnd(2, "0"));
  return sign ? -cents : cents;
}

/** 4050 → "40.50" (el formato que acepta la API). */
export function fromCents(cents: number): Money {
  const sign = cents < 0 ? "-" : "";
  const abs = Math.abs(cents);
  return `${sign}${Math.floor(abs / 100)}.${String(abs % 100).padStart(2, "0")}`;
}

export function isValidMoney(value: string): boolean {
  return MONEY_PATTERN.test(value.trim()) && toCents(value) > 0;
}

const formatters = new Map<string, Intl.NumberFormat>();

/** Formatea para mostrar: formatMoney("1250.5", "USD") → "US$ 1.250,50" (según locale es-VE). */
export function formatMoney(value: Money | number, currency = "USD"): string {
  const cents = typeof value === "number" ? value : toCents(value);
  let formatter = formatters.get(currency);
  if (!formatter) {
    formatter = new Intl.NumberFormat("es-VE", { style: "currency", currency, minimumFractionDigits: 2 });
    formatters.set(currency, formatter);
  }
  return formatter.format(cents / 100);
}
