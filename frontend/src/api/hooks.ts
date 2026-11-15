/**
 * Acceso a datos con TanStack Query: caché, reintentos y estados de carga.
 *
 * Tras cualquier cambio (crear, editar, cambiar estado) se invalidan las
 * consultas relacionadas, de modo que tablas y métricas se refrescan solas.
 */
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../lib/api";
import type {
  Agenda,
  Customer,
  DashboardSummary,
  MonthlyRevenue,
  Rental,
  RentalStatus,
  User,
  Vehicle,
  VehicleStatus,
} from "../types";

export const PAGE_SIZE = 20;

// ------------------------------------------------------------------ lecturas
export function useVehicles(params: { q?: string; status?: VehicleStatus | ""; offset?: number }) {
  return useQuery({
    queryKey: ["vehicles", params],
    queryFn: () => api.list<Vehicle>("/vehicles", { ...params, limit: PAGE_SIZE }),
    placeholderData: keepPreviousData, // la tabla no "parpadea" al paginar o buscar
  });
}

export function useAvailableVehicles(start: string, end: string, enabled: boolean) {
  return useQuery({
    queryKey: ["vehicles", "available", start, end],
    queryFn: () => api.get<Vehicle[]>("/vehicles/available", { start_date: start, end_date: end }),
    enabled,
  });
}

export function useCustomers(params: { q?: string; offset?: number; limit?: number }) {
  return useQuery({
    queryKey: ["customers", params],
    queryFn: () => api.list<Customer>("/customers", { limit: PAGE_SIZE, ...params }),
    placeholderData: keepPreviousData,
  });
}

export function useRentals(params: { q?: string; status?: RentalStatus | ""; offset?: number }) {
  return useQuery({
    queryKey: ["rentals", params],
    queryFn: () => api.list<Rental>("/rentals", { ...params, limit: PAGE_SIZE }),
    placeholderData: keepPreviousData,
  });
}

export function useDashboard() {
  return useQuery({ queryKey: ["dashboard", "summary"], queryFn: () => api.get<DashboardSummary>("/dashboard/summary") });
}

export function useAgenda() {
  return useQuery({ queryKey: ["dashboard", "agenda"], queryFn: () => api.get<Agenda>("/dashboard/agenda") });
}

export function useRevenue(months = 6) {
  return useQuery({
    queryKey: ["dashboard", "revenue", months],
    queryFn: () => api.get<MonthlyRevenue[]>("/dashboard/revenue", { months }),
  });
}

export function useUsers() {
  return useQuery({ queryKey: ["users"], queryFn: () => api.get<User[]>("/users") });
}

// ------------------------------------------------------------------ escrituras
function useInvalidate() {
  const queryClient = useQueryClient();
  return (...keys: string[]) => Promise.all(keys.map((key) => queryClient.invalidateQueries({ queryKey: [key] })));
}

export type VehicleInput = Omit<Vehicle, "id" | "status"> & { status?: VehicleStatus };
export type CustomerInput = Omit<Customer, "id">;

export function useSaveVehicle() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: ({ id, data }: { id?: string; data: Partial<VehicleInput> }) =>
      id ? api.patch<Vehicle>(`/vehicles/${id}`, data) : api.post<Vehicle>("/vehicles", data),
    onSuccess: () => invalidate("vehicles", "dashboard"),
  });
}

export function useDeleteVehicle() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (id: string) => api.delete(`/vehicles/${id}`),
    onSuccess: () => invalidate("vehicles", "dashboard"),
  });
}

export function useSaveCustomer() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: ({ id, data }: { id?: string; data: Partial<CustomerInput> }) =>
      id ? api.patch<Customer>(`/customers/${id}`, data) : api.post<Customer>("/customers", data),
    onSuccess: () => invalidate("customers", "rentals"),
  });
}

export function useDeleteCustomer() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (id: string) => api.delete(`/customers/${id}`),
    onSuccess: () => invalidate("customers"),
  });
}

export function useCreateRental() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (data: { vehicle_id: string; customer_id: string; start_date: string; end_date: string; notes?: string }) =>
      api.post<Rental>("/rentals", data),
    onSuccess: () => invalidate("rentals", "vehicles", "dashboard"),
  });
}

export function useChangeRentalStatus() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: RentalStatus }) =>
      api.post<Rental>(`/rentals/${id}/status`, { status }),
    onSuccess: () => invalidate("rentals", "vehicles", "dashboard"),
  });
}

export function useCreateAgent() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (data: { email: string; full_name: string; password: string }) => api.post<User>("/users", data),
    onSuccess: () => invalidate("users"),
  });
}

export function useDeactivateUser() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (id: string) => api.post<User>(`/users/${id}/deactivate`),
    onSuccess: () => invalidate("users"),
  });
}
