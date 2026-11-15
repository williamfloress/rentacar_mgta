import { ClipboardList, Pencil, Plus, Trash2, Users } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router";

import { PAGE_SIZE, useCustomers, useDeleteCustomer } from "../api/hooks";
import { useAuth } from "../auth/AuthProvider";
import { useToast } from "../components/Toaster";
import {
  Button,
  Card,
  ConfirmDialog,
  EmptyState,
  ErrorState,
  Modal,
  PageHeader,
  Pagination,
  SearchInput,
  Spinner,
  Table,
  Td,
  Th,
} from "../components/ui";
import { errorMessage } from "../lib/errors";
import { useDebounced } from "../lib/useDebounced";
import type { Customer } from "../types";
import { CustomerForm } from "./CustomerForm";

export function CustomersPage() {
  const { isOwner } = useAuth();
  const toast = useToast();
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const [editing, setEditing] = useState<Customer | "new" | null>(null);
  const [deleting, setDeleting] = useState<Customer | null>(null);
  const q = useDebounced(search.trim(), 300);
  const customers = useCustomers({ q, offset });
  const remove = useDeleteCustomer();

  const confirmDelete = () => {
    if (!deleting) return;
    remove.mutate(deleting.id, {
      onSuccess: () => toast.success("Cliente eliminado."),
      onError: (error) => toast.error(errorMessage(error)),
      onSettled: () => setDeleting(null),
    });
  };

  return (
    <>
      <PageHeader
        title="Clientes"
        description="Las personas que alquilan en tu agencia."
        actions={
          <Button icon={<Plus className="size-4" />} onClick={() => setEditing("new")}>
            Nuevo cliente
          </Button>
        }
      />

      <Card>
        <div className="border-b border-line p-4">
          <SearchInput
            value={search}
            onChange={(value) => {
              setSearch(value);
              setOffset(0);
            }}
            placeholder="Buscar por nombre o documento"
            className="md:w-96"
          />
        </div>

        {customers.isPending ? (
          <Spinner />
        ) : customers.isError ? (
          <ErrorState message={errorMessage(customers.error)} onRetry={() => customers.refetch()} />
        ) : customers.data.items.length === 0 ? (
          <EmptyState
            icon={<Users className="size-6" />}
            title={q ? "Ningún cliente coincide" : "Aún no hay clientes"}
            description={q ? "Prueba con otro nombre o documento." : "Registra a tu primer cliente; también puedes hacerlo al crear un alquiler."}
          />
        ) : (
          <>
            <Table>
              <thead>
                <tr>
                  <Th>Cliente</Th>
                  <Th>Documento</Th>
                  <Th className="hidden md:table-cell">Contacto</Th>
                  <Th className="hidden lg:table-cell">Dirección</Th>
                  <Th>
                    <span className="sr-only">Acciones</span>
                  </Th>
                </tr>
              </thead>
              <tbody className={customers.isPlaceholderData ? "opacity-60" : undefined}>
                {customers.data.items.map((customer) => (
                  <tr key={customer.id} className="hover:bg-subtle/50">
                    <Td className="font-medium text-ink">{customer.full_name}</Td>
                    <Td className="font-mono text-sm text-muted">{customer.document_id}</Td>
                    <Td className="hidden md:table-cell">
                      <p className="text-ink">{customer.phone ?? "—"}</p>
                      {customer.email && <p className="text-xs text-muted">{customer.email}</p>}
                    </Td>
                    <Td className="hidden max-w-56 truncate text-muted lg:table-cell">{customer.address ?? "—"}</Td>
                    <Td>
                      <div className="flex justify-end gap-1">
                        <Link
                          to={`/rentals?q=${encodeURIComponent(customer.document_id)}`}
                          className="inline-flex h-8 items-center rounded-lg px-3 text-muted hover:bg-subtle hover:text-ink"
                          aria-label={`Ver alquileres de ${customer.full_name}`}
                          title="Ver alquileres"
                        >
                          <ClipboardList className="size-4" />
                        </Link>
                        <Button variant="ghost" size="sm" onClick={() => setEditing(customer)} aria-label={`Editar ${customer.full_name}`}>
                          <Pencil className="size-4" />
                        </Button>
                        {isOwner && (
                          <Button variant="ghost" size="sm" onClick={() => setDeleting(customer)} aria-label={`Eliminar ${customer.full_name}`}>
                            <Trash2 className="size-4" />
                          </Button>
                        )}
                      </div>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </Table>
            <Pagination offset={offset} limit={PAGE_SIZE} total={customers.data.total} onChange={setOffset} />
          </>
        )}
      </Card>

      <Modal open={editing !== null} onClose={() => setEditing(null)} title={editing === "new" ? "Nuevo cliente" : "Editar cliente"}>
        {editing !== null && (
          <CustomerForm key={editing === "new" ? "new" : editing.id} customer={editing === "new" ? null : editing} onDone={() => setEditing(null)} />
        )}
      </Modal>

      <ConfirmDialog
        open={deleting !== null}
        title="Eliminar cliente"
        message={
          <>
            ¿Eliminar a <b className="text-ink">{deleting?.full_name}</b>? Los clientes con historial de alquileres no se pueden
            borrar.
          </>
        }
        confirmLabel="Eliminar"
        tone="danger"
        loading={remove.isPending}
        onConfirm={confirmDelete}
        onClose={() => setDeleting(null)}
      />
    </>
  );
}
