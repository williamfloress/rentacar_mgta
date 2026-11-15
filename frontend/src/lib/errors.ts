/**
 * Traduce los errores de la API (en inglés, pensados para desarrolladores) a
 * mensajes claros para quien usa el panel.
 */
import { ApiError } from "./api";

const KNOWN_DETAILS: [RegExp, string][] = [
  [/already booked/i, "Ese vehículo ya está reservado en esas fechas. Elige otras fechas u otro vehículo."],
  [/plate already exists/i, "Ya existe un vehículo con esa placa."],
  [/customer with that document/i, "Ya existe un cliente con ese documento."],
  [/email already registered/i, "Ese email ya está registrado."],
  [/incorrect email or password/i, "Email o contraseña incorrectos."],
  [/too many attempts/i, "Demasiados intentos. Espera un minuto y vuelve a probar."],
  [/rental history; set its status/i, "Este vehículo tiene historial de alquileres: no se puede borrar, pero puedes darlo de baja."],
  [/customer has rental history/i, "Este cliente tiene historial de alquileres y no se puede borrar."],
  [/pending or ongoing rental/i, "El vehículo tiene reservas pendientes o en curso. Resuélvelas antes de cambiar su estado."],
  [/cannot start before/i, "Aún no se puede entregar: la reserva empieza más adelante."],
  [/cannot change a rental/i, "Ese cambio de estado no está permitido."],
  [/not available for rental/i, "El vehículo no está disponible para alquilar."],
  [/still out with an overdue return/i, "Ese vehículo sigue fuera: su devolución está atrasada. Regístrala antes de volver a alquilarlo."],
  [/start_date cannot be in the past/i, "La fecha de inicio no puede estar en el pasado."],
  [/end_date must be after/i, "La fecha de devolución debe ser posterior a la de inicio."],
  [/cannot deactivate your own/i, "No puedes desactivar tu propia cuenta."],
  [/owner role required/i, "Solo el dueño de la agencia puede hacer esto."],
  [/not found/i, "No se encontró el registro (puede que se haya eliminado)."],
];

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 0) return "No se pudo conectar con el servidor. Revisa tu conexión.";
    for (const [pattern, message] of KNOWN_DETAILS) {
      if (pattern.test(error.detail)) return message;
    }
    if (error.status === 422) return `Datos no válidos (${error.detail}).`;
    if (error.status >= 500) return "Error del servidor. Inténtalo de nuevo en unos segundos.";
    return error.detail;
  }
  return "Ocurrió un error inesperado.";
}
