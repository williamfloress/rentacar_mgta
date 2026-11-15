import clsx from "clsx";
import { CalendarPlus, Car, ClipboardList, LayoutDashboard, LogOut, Menu, UserCog, Users, X } from "lucide-react";
import { useState, type ReactNode } from "react";
import { NavLink, Outlet } from "react-router";

import { useAuth } from "../auth/AuthProvider";
import { Logo } from "./Logo";

interface NavItem {
  to: string;
  label: string;
  icon: ReactNode;
  ownerOnly?: boolean;
}

const NAV: NavItem[] = [
  { to: "/", label: "Panel", icon: <LayoutDashboard className="size-4" /> },
  { to: "/rentals", label: "Alquileres", icon: <ClipboardList className="size-4" /> },
  { to: "/vehicles", label: "Flota", icon: <Car className="size-4" /> },
  { to: "/customers", label: "Clientes", icon: <Users className="size-4" /> },
  { to: "/team", label: "Equipo", icon: <UserCog className="size-4" />, ownerOnly: true },
];

function initials(name: string): string {
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const { user, isOwner, logout } = useAuth();
  return (
    <div className="flex h-full flex-col bg-brand-900 text-blue-100">
      <div className="px-5 pt-5 pb-6">
        <Logo inverted />
        {user && <p className="mt-3 truncate text-xs text-blue-300">{user.agency_name}</p>}
      </div>

      <div className="px-3">
        <NavLink
          to="/rentals/new"
          onClick={onNavigate}
          className="mb-4 flex h-10 items-center justify-center gap-2 rounded-lg bg-white text-sm font-semibold text-brand-800 shadow-sm transition hover:bg-blue-50"
        >
          <CalendarPlus className="size-4" />
          Nuevo alquiler
        </NavLink>
      </div>

      <nav className="flex-1 space-y-0.5 px-3" aria-label="Navegación principal">
        {NAV.filter((item) => !item.ownerOnly || isOwner).map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/" || item.to === "/rentals"}
            onClick={onNavigate}
            className={({ isActive }) =>
              clsx(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                isActive ? "bg-white/10 text-white" : "text-blue-200 hover:bg-white/5 hover:text-white",
              )
            }
          >
            {item.icon}
            {item.label}
          </NavLink>
        ))}
      </nav>

      {user && (
        <div className="m-3 flex items-center gap-3 rounded-xl bg-white/5 p-3">
          <div className="flex size-9 shrink-0 items-center justify-center rounded-full bg-brand-600 text-xs font-semibold text-white" aria-hidden>
            {initials(user.full_name)}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-white">{user.full_name}</p>
            <p className="truncate text-xs text-blue-300">{user.role === "owner" ? "Dueño" : "Agente"}</p>
          </div>
          <button
            type="button"
            onClick={logout}
            className="rounded-lg p-2 text-blue-200 hover:bg-white/10 hover:text-white"
            aria-label="Cerrar sesión"
            title="Cerrar sesión"
          >
            <LogOut className="size-4" />
          </button>
        </div>
      )}
    </div>
  );
}

export function AppLayout() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="min-h-dvh lg:pl-64">
      {/* Escritorio: barra lateral fija */}
      <aside className="fixed inset-y-0 left-0 hidden w-64 lg:block">
        <Sidebar />
      </aside>

      {/* Móvil: barra superior + menú desplegable */}
      <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-line bg-surface/95 px-4 backdrop-blur lg:hidden">
        <Logo />
        <button type="button" onClick={() => setMobileOpen(true)} className="rounded-lg p-2 text-muted hover:bg-subtle" aria-label="Abrir menú">
          <Menu className="size-5" />
        </button>
      </header>
      {mobileOpen && (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true" aria-label="Menú">
          <div className="absolute inset-0 bg-slate-900/50" onClick={() => setMobileOpen(false)} />
          <div className="absolute inset-y-0 left-0 w-72 max-w-[85%] shadow-2xl">
            <Sidebar onNavigate={() => setMobileOpen(false)} />
            <button
              type="button"
              onClick={() => setMobileOpen(false)}
              className="absolute top-4 right-3 rounded-lg p-1.5 text-blue-200 hover:bg-white/10"
              aria-label="Cerrar menú"
            >
              <X className="size-5" />
            </button>
          </div>
        </div>
      )}

      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
        <Outlet />
      </main>
    </div>
  );
}
