import { describe, expect, it } from "vitest";

import { ApiError, buildUrl } from "../api";
import { errorMessage } from "../errors";
import { isOverdue } from "../labels";

describe("errorMessage", () => {
  it("translates known API errors", () => {
    expect(errorMessage(new ApiError(409, "Vehicle is already booked in that period"))).toMatch(/ya está reservado/);
    expect(errorMessage(new ApiError(0, "Network error"))).toMatch(/conectar/);
    expect(errorMessage(new ApiError(503, "boom"))).toMatch(/servidor/);
    expect(errorMessage(new Error("x"))).toMatch(/inesperado/);
  });
});

describe("buildUrl", () => {
  it("skips empty params", () => {
    const url = new URL(buildUrl("/vehicles", { q: "", status: undefined, limit: 20 }));
    expect(url.pathname).toBe("/vehicles");
    expect(url.search).toBe("?limit=20");
  });
});

describe("isOverdue", () => {
  it("is only true for active rentals past their end date", () => {
    expect(isOverdue({ status: "active", end_date: "2026-11-10" }, "2026-11-14")).toBe(true);
    expect(isOverdue({ status: "active", end_date: "2026-11-14" }, "2026-11-14")).toBe(false);
    expect(isOverdue({ status: "reserved", end_date: "2026-11-10" }, "2026-11-14")).toBe(false);
  });
});
