/**
 * Sesión del usuario.
 *
 * El token JWT se guarda en localStorage para sobrevivir a recargas. Es un
 * compromiso conocido: una vulnerabilidad XSS podría leerlo. Se mitiga con un
 * token de vida corta, React (que escapa el contenido por defecto) y sin HTML
 * de terceros. La alternativa (cookie httpOnly) exige protección CSRF y que API
 * y frontend compartan dominio; está anotada en docs/04-roadmap.md.
 */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

import { api, configureApi } from "../lib/api";
import type { Me } from "../types";

const TOKEN_KEY = "rentacar.token";

function readToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null; // navegación privada o almacenamiento bloqueado
  }
}

function writeToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* sin almacenamiento la sesión dura lo que la pestaña */
  }
}

interface RegisterInput {
  agency_name: string;
  full_name: string;
  email: string;
  password: string;
}

interface AuthContextValue {
  user: Me | null;
  isLoading: boolean;
  isOwner: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (input: RegisterInput) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [token, setToken] = useState<string | null>(readToken);

  const logout = useCallback(() => {
    writeToken(null);
    setToken(null);
    queryClient.clear(); // nada de datos de la sesión anterior en caché
  }, [queryClient]);

  // Se configura durante el render (no en un efecto) para que las consultas
  // de los hijos ya salgan con el token correcto en el primer render.
  configureApi({ getToken: () => token, onUnauthorized: logout });

  const me = useQuery({
    queryKey: ["me", token],
    queryFn: () => api.get<Me>("/auth/me"),
    enabled: token !== null,
    staleTime: 5 * 60 * 1000,
    retry: false,
  });

  const startSession = useCallback(
    (accessToken: string) => {
      queryClient.clear();
      writeToken(accessToken);
      setToken(accessToken);
    },
    [queryClient],
  );

  const login = useCallback(
    async (email: string, password: string) => {
      const result = await api.postForm<{ access_token: string }>("/auth/login", { username: email, password });
      startSession(result.access_token);
    },
    [startSession],
  );

  const register = useCallback(
    async (input: RegisterInput) => {
      const result = await api.post<{ access_token: string }>("/auth/register", input);
      startSession(result.access_token);
    },
    [startSession],
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      user: token ? (me.data ?? null) : null,
      isLoading: token !== null && me.isPending,
      isOwner: me.data?.role === "owner",
      login,
      register,
      logout,
    }),
    [token, me.data, me.isPending, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside <AuthProvider>");
  return context;
}
