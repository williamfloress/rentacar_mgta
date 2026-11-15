import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { useSaveCustomer } from "../api/hooks";
import { useToast } from "../components/Toaster";
import { Button, Field, Input } from "../components/ui";
import { errorMessage } from "../lib/errors";
import type { Customer } from "../types";

const schema = z.object({
  document_id: z.string().trim().min(3, "Mínimo 3 caracteres").max(30),
  full_name: z.string().trim().min(2, "Mínimo 2 caracteres").max(120),
  phone: z.string().trim().max(30),
  email: z.union([z.literal(""), z.string().trim().email("Email no válido")]),
  address: z.string().trim().max(200),
});
type FormValues = z.infer<typeof schema>;

/** Formulario de cliente; se usa en la página de clientes y al crear un alquiler. */
export function CustomerForm({ customer, onDone }: { customer: Customer | null; onDone: (saved?: Customer) => void }) {
  const toast = useToast();
  const save = useSaveCustomer();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      document_id: customer?.document_id ?? "",
      full_name: customer?.full_name ?? "",
      phone: customer?.phone ?? "",
      email: customer?.email ?? "",
      address: customer?.address ?? "",
    },
  });

  const onSubmit = handleSubmit((values) => {
    // Los campos opcionales vacíos se envían como null, no como "".
    const data = {
      ...values,
      phone: values.phone || null,
      email: values.email || null,
      address: values.address || null,
    };
    save.mutate(
      { id: customer?.id, data },
      {
        onSuccess: (saved) => {
          toast.success(customer ? "Cliente actualizado." : `Cliente ${saved.full_name} registrado.`);
          onDone(saved);
        },
        onError: (error) => toast.error(errorMessage(error)),
      },
    );
  });

  return (
    <form onSubmit={onSubmit} className="grid gap-4 sm:grid-cols-2" noValidate>
      <Field label="Documento (cédula, pasaporte…)" error={errors.document_id?.message}>
        {(a11y) => <Input {...a11y} placeholder="V-12.345.678" {...register("document_id")} />}
      </Field>
      <Field label="Nombre completo" error={errors.full_name?.message}>
        {(a11y) => <Input {...a11y} autoComplete="off" {...register("full_name")} />}
      </Field>
      <Field label="Teléfono (opcional)" error={errors.phone?.message}>
        {(a11y) => <Input {...a11y} type="tel" {...register("phone")} />}
      </Field>
      <Field label="Email (opcional)" error={errors.email?.message}>
        {(a11y) => <Input {...a11y} type="email" {...register("email")} />}
      </Field>
      <Field label="Dirección (opcional)" error={errors.address?.message} className="sm:col-span-2">
        {(a11y) => <Input {...a11y} {...register("address")} />}
      </Field>
      <div className="flex justify-end gap-2 sm:col-span-2">
        <Button variant="secondary" onClick={() => onDone()}>
          Cancelar
        </Button>
        <Button type="submit" loading={save.isPending}>
          {customer ? "Guardar cambios" : "Registrar cliente"}
        </Button>
      </div>
    </form>
  );
}
