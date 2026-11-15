import { useEffect, useState } from "react";

/** Devuelve `value` tras `delay` ms sin cambios: evita una petición por cada tecla en los buscadores. */
export function useDebounced<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}
