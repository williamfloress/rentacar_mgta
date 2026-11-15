import { LinkButton } from "../components/ui";

export function NotFoundPage() {
  return (
    <div className="flex flex-col items-center py-24 text-center">
      <p className="text-sm font-semibold text-brand-700">404</p>
      <h1 className="mt-2 text-2xl font-semibold tracking-tight">Esta página no existe</h1>
      <p className="mt-2 text-sm text-muted">Puede que el enlace esté mal escrito o que la página se haya movido.</p>
      <LinkButton to="/" className="mt-6">
        Volver al panel
      </LinkButton>
    </div>
  );
}
