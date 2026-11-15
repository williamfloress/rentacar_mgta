import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight, Sparkles } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link } from "react-router";
import { z } from "zod";

import { useAuth } from "../auth/AuthProvider";
import { Button, Field, Input } from "../components/ui";
import { errorMessage } from "../lib/errors";
import { useSlowFlag } from "../lib/useSlowFlag";
import { AuthShell } from "./AuthShell";

const schema = z.object({
  email: z.string().trim().min(1, "Escribe tu email").email("Email no válido"),
  password: z.string().min(1, "Escribe tu contraseña"),
});
type FormValues = z.infer<typeof schema>;

// Credenciales públicas de la agencia de demostración (las crea backend/app/seed.py).
const DEMO_ACCOUNTS = [
  { label: "Dueño", email: "demo@rentacar.dev" },
  { label: "Agente", email: "agente@rentacar.dev" },
];
const DEMO_PASSWORD = "demo-rentacar";

export function LoginPage() {
  const { login } = useAuth();
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });
  const waking = useSlowFlag(isSubmitting);

  const onSubmit = handleSubmit(async ({ email, password }) => {
    setServerError(null);
    try {
      await login(email, password);
    } catch (error) {
      setServerError(errorMessage(error));
    }
  });

  const enterDemo = (email: string) => {
    setValue("email", email, { shouldValidate: true });
    setValue("password", DEMO_PASSWORD, { shouldValidate: true });
    void onSubmit();
  };

  return (
    <AuthShell title="Inicia sesión" subtitle="Accede al panel de tu agencia.">
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <Field label="Email" error={errors.email?.message}>
          {(a11y) => <Input {...a11y} type="email" autoComplete="email" {...register("email")} />}
        </Field>
        <Field label="Contraseña" error={errors.password?.message}>
          {(a11y) => <Input {...a11y} type="password" autoComplete="current-password" {...register("password")} />}
        </Field>
        {serverError && (
          <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            {serverError}
          </p>
        )}
        <Button type="submit" loading={isSubmitting} className="w-full">
          Entrar
          <ArrowRight className="size-4" />
        </Button>
        {waking && (
          <p role="status" className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-900">
            Despertando el servidor… La demo está en un plan gratuito que se duerme tras un rato sin uso; la primera
            petición puede tardar hasta un minuto.
          </p>
        )}
      </form>

      <div className="mt-6 rounded-xl border border-brand-100 bg-brand-50 p-4">
        <p className="flex items-center gap-2 text-sm font-medium text-brand-800">
          <Sparkles className="size-4" aria-hidden />
          ¿Solo quieres probarlo?
        </p>
        <p className="mt-1 text-xs text-brand-800/80">
          Entra en una agencia de demostración con 6 meses de datos. Se restablece en cada reinicio del servidor.
        </p>
        <div className="mt-3 grid grid-cols-2 gap-2">
          {DEMO_ACCOUNTS.map((account) => (
            <Button key={account.email} variant="secondary" size="sm" onClick={() => enterDemo(account.email)} disabled={isSubmitting}>
              Demo como {account.label.toLowerCase()}
            </Button>
          ))}
        </div>
      </div>

      <p className="mt-8 text-center text-sm text-muted">
        ¿Tienes una agencia?{" "}
        <Link to="/register" className="font-medium text-brand-700 hover:underline">
          Regístrala gratis
        </Link>
      </p>
    </AuthShell>
  );
}
