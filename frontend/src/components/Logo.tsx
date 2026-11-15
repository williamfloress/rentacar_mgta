import clsx from "clsx";
import { Car } from "lucide-react";

export function Logo({ inverted = false }: { inverted?: boolean }) {
  return (
    <span className="inline-flex items-center gap-2">
      <span className={clsx("flex size-8 items-center justify-center rounded-lg", inverted ? "bg-white text-brand-800" : "bg-brand-700 text-white")}>
        <Car className="size-[18px]" aria-hidden />
      </span>
      <span className={clsx("text-lg font-semibold tracking-tight", inverted ? "text-white" : "text-ink")}>
        rent-a-<span className={inverted ? "text-blue-300" : "text-brand-700"}>CAR</span>
      </span>
    </span>
  );
}
