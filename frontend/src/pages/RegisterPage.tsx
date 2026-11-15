import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link } from "react-router";
import { z } from "zod";

import { useAuth } from "../auth/AuthProvider";
import { Button, Field, Input } from "../components/ui";
import { errorMessage } from "../lib/errors";
import { AuthShell } from "./AuthShell";

const schema = z.object({
  agency_name: z.string().trim().min(2, "Mínimo 2 caracteres").max(120),
  full_name: z.string().trim().min(2, "Mínimo 2 caracteres").max(120),
  email: z.string().trim().email("Email no válido"),
  // Misma regla que la API: longitud antes que "complejidad" (recomendación NIST).
  password: z.string().min(10, "Mínimo 10 caracteres").max(128),
});
type FormValues = z.infer<typeof schema>;

export function RegisterPage() {
  const { register: registerAgency } = useAuth();
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const onSubmit = handleSubmit(async (values) => {
    setServerError(null);
    try {
      await registerAgency(values);
    } catch (error) {
      setServerError(errorMessage(error));
    }
  });

  return (
    <AuthShell title="Registra tu agencia" subtitle="Serás el dueño de la cuenta y podrás invitar a tu equipo.">
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <Field label="Nombre de la agencia" error={errors.agency_name?.message}>
          {(a11y) => <Input {...a11y} autoComplete="organization" {...register("agency_name")} />}
        </Field>
        <Field label="Tu nombre" error={errors.full_name?.message}>
          {(a11y) => <Input {...a11y} autoComplete="name" {...register("full_name")} />}
        </Field>
        <Field label="Email" error={errors.email?.message}>
          {(a11y) => <Input {...a11y} type="email" autoComplete="email" {...register("email")} />}
        </Field>
        <Field label="Contraseña" error={errors.password?.message} hint="Mínimo 10 caracteres. Una frase es más segura que una palabra rara.">
          {(a11y) => <Input {...a11y} type="password" autoComplete="new-password" {...register("password")} />}
        </Field>
        {serverError && (
          <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            {serverError}
          </p>
        )}
        <Button type="submit" loading={isSubmitting} className="w-full">
          Crear agencia
        </Button>
      </form>
      <p className="mt-8 text-center text-sm text-muted">
        ¿Ya tienes cuenta?{" "}
        <Link to="/login" className="font-medium text-brand-700 hover:underline">
          Inicia sesión
        </Link>
      </p>
    </AuthShell>
  );
}
