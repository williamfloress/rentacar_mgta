import { useEffect, useState } from "react";

/**
 * true si `pending` lleva más de `afterMs` activo. Se usa para avisar del
 * "arranque en frío": en el plan gratuito de Render la API se duerme y la
 * primera petición puede tardar cerca de un minuto.
 */
export function useSlowFlag(pending: boolean, afterMs = 4000): boolean {
  const [slow, setSlow] = useState(false);
  useEffect(() => {
    if (!pending) return;
    const timer = setTimeout(() => setSlow(true), afterMs);
    return () => {
      clearTimeout(timer);
      setSlow(false);
    };
  }, [pending, afterMs]);
  return pending && slow;
}
