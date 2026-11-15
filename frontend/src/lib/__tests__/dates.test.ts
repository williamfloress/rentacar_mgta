import { describe, expect, it } from "vitest";

import { addDays, daysBetween, parseISODate, relativeDay, toISODate } from "../dates";

describe("calendar dates", () => {
  it("parses as local date, not UTC midnight", () => {
    const date = parseISODate("2026-11-14");
    expect([date.getFullYear(), date.getMonth(), date.getDate()]).toEqual([2026, 10, 14]);
    expect(toISODate(date)).toBe("2026-11-14");
  });

  it("adds days across month and year boundaries", () => {
    expect(addDays("2026-12-30", 3)).toBe("2027-01-02");
    expect(addDays("2028-02-28", 1)).toBe("2028-02-29"); // año bisiesto
  });

  it("counts a half-open range like the backend", () => {
    expect(daysBetween("2030-01-10", "2030-01-15")).toBe(5);
    expect(daysBetween("2030-01-10", "2030-01-10")).toBe(0);
  });

  it("describes relative days", () => {
    expect(relativeDay("2026-11-14", "2026-11-14")).toBe("hoy");
    expect(relativeDay("2026-11-15", "2026-11-14")).toBe("mañana");
    expect(relativeDay("2026-11-12", "2026-11-14")).toBe("hace 2 días");
  });
});
