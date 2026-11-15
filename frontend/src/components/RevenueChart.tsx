import { useState } from "react";

import { formatMonth } from "../lib/dates";
import { formatMoney, toCents } from "../lib/money";
import type { MonthlyRevenue } from "../types";

/** Eje con valores "redondos" (0, 5 000, 10 000, 15 000) y unas 3-4 divisiones. */
function niceScale(value: number): { max: number; ticks: number[] } {
  if (value <= 0) return { max: 100, ticks: [0, 100] };
  const rough = value / 3;
  const magnitude = 10 ** Math.floor(Math.log10(rough));
  const step = ([1, 2, 2.5, 5, 10].find((s) => s * magnitude >= rough) ?? 10) * magnitude;
  const max = Math.ceil(value / step) * step;
  return { max, ticks: Array.from({ length: Math.round(max / step) + 1 }, (_, i) => i * step) };
}

/**
 * Barras de ingresos por mes (una sola serie, un solo tono).
 * El mes en curso se dibuja más claro porque aún no ha terminado.
 */
export function RevenueChart({ data, currency }: { data: MonthlyRevenue[]; currency: string }) {
  const [hovered, setHovered] = useState<number | null>(null);
  const values = data.map((d) => toCents(d.revenue));
  const { max, ticks } = niceScale(Math.max(...values, 0));

  return (
    <figure>
      <div className="relative flex h-56 gap-3 pl-14">
        {/* rejilla y eje: discretos para no competir con los datos */}
        {ticks.map((tick) => (
          <div key={tick} className="pointer-events-none absolute right-0 left-14 border-t border-dashed border-line" style={{ bottom: `${(tick / max) * 100}%` }}>
            <span className="absolute -top-2 -left-14 w-12 text-right text-[11px] text-muted tabular-nums">
              {formatMoney(tick, currency).replace(/,00$/, "")}
            </span>
          </div>
        ))}

        {data.map((month, index) => {
          const value = values[index] ?? 0;
          const isCurrent = index === data.length - 1;
          const isHovered = hovered === index;
          return (
            <div
              key={month.month}
              className="relative flex flex-1 items-end justify-center"
              onMouseEnter={() => setHovered(index)}
              onMouseLeave={() => setHovered(null)}
              onFocus={() => setHovered(index)}
              onBlur={() => setHovered(null)}
              tabIndex={0}
              aria-label={`${formatMonth(month.month)}: ${formatMoney(month.revenue, currency)}, ${month.rentals} alquileres`}
            >
              <div
                className={`w-full max-w-12 rounded-t-[4px] transition-colors ${
                  isCurrent ? "bg-brand-500/45" : isHovered ? "bg-brand-800" : "bg-brand-600"
                }`}
                style={{ height: `${(value / max) * 100}%`, minHeight: value > 0 ? 2 : 0 }}
              />
              {isHovered && (
                <div className="absolute bottom-full z-10 mb-2 rounded-lg border border-line bg-surface px-3 py-2 text-xs whitespace-nowrap shadow-lg" role="tooltip">
                  <p className="font-medium text-ink capitalize">{formatMonth(month.month)}{isCurrent && " (en curso)"}</p>
                  <p className="mt-0.5 text-ink tabular-nums">{formatMoney(month.revenue, currency)}</p>
                  <p className="text-muted">{month.rentals} alquileres</p>
                </div>
              )}
            </div>
          );
        })}
      </div>
      <div className="mt-2 flex gap-3 pl-14">
        {data.map((month, index) => (
          <span key={month.month} className="flex-1 text-center text-xs text-muted">
            <span className="capitalize">{formatMonth(month.month)}</span>
            {index === data.length - 1 && <span className="block text-[10px]">en curso</span>}
          </span>
        ))}
      </div>
      {/* Versión en tabla para lectores de pantalla */}
      <table className="sr-only">
        <caption>Ingresos por mes</caption>
        <tbody>
          {data.map((month) => (
            <tr key={month.month}>
              <th scope="row">{formatMonth(month.month)}</th>
              <td>{formatMoney(month.revenue, currency)}</td>
              <td>{month.rentals} alquileres</td>
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}
