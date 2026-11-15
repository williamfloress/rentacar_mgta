import type { ReactNode } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router";

import { useAuth } from "./auth/AuthProvider";
import { AppLayout } from "./components/AppLayout";
import { Spinner } from "./components/ui";
import { CustomersPage } from "./pages/CustomersPage";
import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";
import { NewRentalPage } from "./pages/NewRentalPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { RegisterPage } from "./pages/RegisterPage";
import { RentalsPage } from "./pages/RentalsPage";
import { TeamPage } from "./pages/TeamPage";
import { VehiclesPage } from "./pages/VehiclesPage";

function RequireAuth({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth();
  const location = useLocation();
  if (isLoading) return <Spinner label="Abriendo sesión…" />;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  return children;
}

function RequireOwner({ children }: { children: ReactNode }) {
  const { isOwner } = useAuth();
  return isOwner ? children : <Navigate to="/" replace />;
}

function GuestOnly({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth();
  if (isLoading) return <Spinner />;
  return user ? <Navigate to="/" replace /> : children;
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<GuestOnly><LoginPage /></GuestOnly>} />
      <Route path="/register" element={<GuestOnly><RegisterPage /></GuestOnly>} />
      <Route element={<RequireAuth><AppLayout /></RequireAuth>}>
        <Route index element={<DashboardPage />} />
        <Route path="rentals" element={<RentalsPage />} />
        <Route path="rentals/new" element={<NewRentalPage />} />
        <Route path="vehicles" element={<VehiclesPage />} />
        <Route path="customers" element={<CustomersPage />} />
        <Route path="team" element={<RequireOwner><TeamPage /></RequireOwner>} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
