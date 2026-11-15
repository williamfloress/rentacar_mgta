import { zodResolver } from "@hookform/resolvers/zod";
import { Plus } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { useCreateAgent, useDeactivateUser, useUsers } from "../api/hooks";
import { useAuth } from "../auth/AuthProvider";
import { useToast } from "../components/Toaster";
import { Badge, Button, Card, ConfirmDialog, ErrorState, Field, Input, Modal, PageHeader, Spinner, Table, Td, Th } from "../components/ui";
import { errorMessage } from "../lib/errors";
import type { User } from "../types";

const schema = z.object({
  full_name: z.string().trim().min(2, "Mínimo 2 caracteres").max(120),
  email: z.string().trim().email("Email no válido"),
  password: z.string().min(10, "Mínimo 10 caracteres").max(128),
});
type FormValues = z.infer<typeof schema>;

function AgentForm({ onDone }: { onDone: () => void }) {
  const toast = useToast();
  const create = useCreateAgent();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const onSubmit = handleSubmit((values) =>
    create.mutate(values, {
      onSuccess: (agent) => {
        toast.success(`${agent.full_name} ya puede iniciar sesión.`);
        onDone();
      },
      onError: (error) => toast.error(errorMessage(error)),
    }),
  );

  return (
    <form onSubmit={onSubmit} className="space-y-4" noValidate>
      <Field label="Nombre completo" error={errors.full_name?.message}>
        {(a11y) => <Input {...a11y} {...register("full_name")} />}
      </Field>
      <Field label="Email" error={errors.email?.message}>
        {(a11y) => <Input {...a11y} type="email" autoComplete="off" {...register("email")} />}
      </Field>
      <Field label="Contraseña inicial" error={errors.password?.message} hint="Compártela por un canal seguro. Mínimo 10 caracteres.">
        {(a11y) => <Input {...a11y} type="password" autoComplete="new-password" {...register("password")} />}
      </Field>
      <div className="flex justify-end gap-2">
        <Button variant="secondary" onClick={onDone}>
          Cancelar
        </Button>
        <Button type="submit" loading={create.isPending}>
          Crear agente
        </Button>
      </div>
    </form>
  );
}

export function TeamPage() {
  const { user: me } = useAuth();
  const toast = useToast();
  const users = useUsers();
  const deactivate = useDeactivateUser();
  const [adding, setAdding] = useState(false);
  const [target, setTarget] = useState<User | null>(null);

  const confirmDeactivate = () => {
    if (!target) return;
    deactivate.mutate(target.id, {
      onSuccess: () => toast.success(`Se desactivó la cuenta de ${target.full_name}.`),
      onError: (error) => toast.error(errorMessage(error)),
      onSettled: () => setTarget(null),
    });
  };

  return (
    <>
      <PageHeader
        title="Equipo"
        description="Los agentes operan flota, clientes y alquileres. Solo el dueño puede borrar datos y gestionar el equipo."
        actions={
          <Button icon={<Plus className="size-4" />} onClick={() => setAdding(true)}>
            Añadir agente
          </Button>
        }
      />
      <Card>
        {users.isPending ? (
          <Spinner />
        ) : users.isError ? (
          <ErrorState message={errorMessage(users.error)} onRetry={() => users.refetch()} />
        ) : (
          <Table>
            <thead>
              <tr>
                <Th>Nombre</Th>
                <Th>Email</Th>
                <Th>Rol</Th>
                <Th>Estado</Th>
                <Th>
                  <span className="sr-only">Acciones</span>
                </Th>
              </tr>
            </thead>
            <tbody>
              {users.data.map((member) => (
                <tr key={member.id}>
                  <Td className="font-medium text-ink">
                    {member.full_name}
                    {member.id === me?.id && <span className="ml-2 text-xs font-normal text-muted">(tú)</span>}
                  </Td>
                  <Td className="text-muted">{member.email}</Td>
                  <Td>{member.role === "owner" ? "Dueño" : "Agente"}</Td>
                  <Td>{member.is_active ? <Badge tone="green">Activo</Badge> : <Badge>Desactivado</Badge>}</Td>
                  <Td className="text-right">
                    {member.is_active && member.id !== me?.id && (
                      <Button variant="ghost" size="sm" onClick={() => setTarget(member)}>
                        Desactivar
                      </Button>
                    )}
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>

      <Modal open={adding} onClose={() => setAdding(false)} title="Añadir agente" size="sm">
        {adding && <AgentForm onDone={() => setAdding(false)} />}
      </Modal>
      <ConfirmDialog
        open={target !== null}
        title="Desactivar cuenta"
        message={
          <>
            <b className="text-ink">{target?.full_name}</b> perderá el acceso de inmediato, incluso si tiene una sesión abierta. Su
            historial se conserva.
          </>
        }
        confirmLabel="Desactivar"
        tone="danger"
        loading={deactivate.isPending}
        onConfirm={confirmDeactivate}
        onClose={() => setTarget(null)}
      />
    </>
  );
}
