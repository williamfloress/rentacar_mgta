import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AuthProvider } from "../auth/AuthProvider";
import { LoginPage } from "./LoginPage";

function renderLogin() {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => vi.unstubAllGlobals());

describe("LoginPage", () => {
  it("validates fields before calling the API", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    renderLogin();

    await userEvent.click(screen.getByRole("button", { name: /entrar/i }));

    expect(await screen.findByText("Escribe tu email")).toBeInTheDocument();
    expect(screen.getByText("Escribe tu contraseña")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("shows a translated message when credentials are wrong", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "Incorrect email or password" }), { status: 401 })),
    );
    renderLogin();

    await userEvent.type(screen.getByLabelText("Email"), "ana@demo.com");
    await userEvent.type(screen.getByLabelText("Contraseña"), "wrong-password");
    await userEvent.click(screen.getByRole("button", { name: /entrar/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Email o contraseña incorrectos.");
  });

  it("sends the OAuth2 form to /auth/login", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "x" }), { status: 401 }));
    vi.stubGlobal("fetch", fetchMock);
    renderLogin();

    await userEvent.click(screen.getByRole("button", { name: /demo como dueño/i }));

    await screen.findByRole("alert");
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toMatch(/\/auth\/login$/);
    expect(String(init.body)).toBe("username=demo%40rentacar.dev&password=demo-rentacar");
  });
});
