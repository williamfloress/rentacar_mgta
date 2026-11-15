/**
 * Cliente HTTP mínimo sobre fetch.
 *
 * - Añade el token (cabecera Authorization) a cada petición.
 * - Convierte las respuestas de error en ApiError con el código HTTP y el
 *   detalle que devuelve FastAPI, para que la UI decida qué mostrar.
 * - Los listados leen el total de la cabecera X-Total-Count (paginación).
 */
import type { Paginated } from "../types";

export const API_URL = (import.meta.env.VITE_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

type Params = Record<string, string | number | boolean | null | undefined>;

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  params?: Params;
  json?: unknown;
  form?: Record<string, string>;
}

let getToken: () => string | null = () => null;
let onUnauthorized: () => void = () => {};

/** Lo llama AuthProvider para conectar el cliente con la sesión. */
export function configureApi(options: { getToken: () => string | null; onUnauthorized: () => void }) {
  getToken = options.getToken;
  onUnauthorized = options.onUnauthorized;
}

export function buildUrl(path: string, params?: Params): string {
  const url = new URL(API_URL + path);
  for (const [key, value] of Object.entries(params ?? {})) {
    if (value !== undefined && value !== null && value !== "") url.searchParams.set(key, String(value));
  }
  return url.toString();
}

/** FastAPI devuelve `detail` como texto, o como lista de errores de validación (422). */
function readDetail(body: unknown): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as { msg?: string; loc?: unknown[] };
      const field = Array.isArray(first.loc) ? first.loc[first.loc.length - 1] : undefined;
      return [field, first.msg].filter(Boolean).join(": ");
    }
  }
  return "Unexpected error";
}

async function send(path: string, { method = "GET", params, json, form }: RequestOptions = {}) {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let body: BodyInit | undefined;
  if (json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(json);
  } else if (form) {
    body = new URLSearchParams(form);
  }

  let response: Response;
  try {
    response = await fetch(buildUrl(path, params), { method, headers, body });
  } catch {
    throw new ApiError(0, "Network error");
  }

  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    // Un 401 con token significa sesión caducada o usuario desactivado.
    if (response.status === 401 && token) onUnauthorized();
    throw new ApiError(response.status, readDetail(payload));
  }
  return response;
}

export const api = {
  async get<T>(path: string, params?: Params): Promise<T> {
    return (await send(path, { params })).json() as Promise<T>;
  },

  async list<T>(path: string, params?: Params): Promise<Paginated<T>> {
    const response = await send(path, { params });
    const items = (await response.json()) as T[];
    const total = Number(response.headers.get("X-Total-Count") ?? items.length);
    return { items, total };
  },

  async post<T>(path: string, json?: unknown): Promise<T> {
    return (await send(path, { method: "POST", json })).json() as Promise<T>;
  },

  async postForm<T>(path: string, form: Record<string, string>): Promise<T> {
    return (await send(path, { method: "POST", form })).json() as Promise<T>;
  },

  async patch<T>(path: string, json: unknown): Promise<T> {
    return (await send(path, { method: "PATCH", json })).json() as Promise<T>;
  },

  async delete(path: string): Promise<void> {
    await send(path, { method: "DELETE" });
  },
};
