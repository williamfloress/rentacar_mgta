/**
 * Tipos de la API (reflejan los esquemas Pydantic de backend/app/schemas.py).
 *
 * El dinero llega como TEXTO ("40.00"): la API usa Decimal para no perder
 * precisión. Aquí se mantiene como string y solo se convierte para mostrarlo
 * o para calcular en céntimos enteros (ver lib/money.ts).
 */
export type Money = string;
export type ISODate = string; // "2026-11-14"

export type Role = "owner" | "agent";

export interface Me {
  id: string;
  tenant_id: string;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
  agency_name: string;
  currency: string;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
}

export type VehicleStatus = "active" | "maintenance" | "retired";

export interface Vehicle {
  id: string;
  plate: string;
  brand: string;
  model: string;
  color: string | null;
  year: number;
  daily_rate: Money;
  status: VehicleStatus;
}

export interface Customer {
  id: string;
  document_id: string;
  full_name: string;
  phone: string | null;
  email: string | null;
  address: string | null;
}

export type RentalStatus = "reserved" | "active" | "returned" | "cancelled";

export interface Rental {
  id: string;
  start_date: ISODate;
  end_date: ISODate;
  daily_rate_snapshot: Money;
  total_amount: Money;
  late_fee: Money;
  status: RentalStatus;
  returned_at: string | null;
  notes: string | null;
  created_at: string;
  vehicle: Vehicle;
  customer: Customer;
}

export interface DashboardSummary {
  vehicles_total: number;
  vehicles_available_today: number;
  rentals_active: number;
  rentals_reserved: number;
  rentals_overdue: number;
  revenue_current_month: Money;
}

export interface Agenda {
  today: ISODate;
  pickups: Rental[];
  returns: Rental[];
}

export interface MonthlyRevenue {
  month: ISODate;
  revenue: Money;
  rentals: number;
}

export interface Paginated<T> {
  items: T[];
  total: number;
}
