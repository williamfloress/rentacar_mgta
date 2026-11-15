import { describe, expect, it } from "vitest";

import { formatMoney, fromCents, isValidMoney, toCents } from "../money";

describe("toCents", () => {
  it("parses API decimal strings exactly", () => {
    expect(toCents("40.00")).toBe(4000);
    expect(toCents("40.5")).toBe(4050);
    expect(toCents("0.07")).toBe(7);
    expect(toCents("13655")).toBe(1365500);
  });

  it("avoids floating point artifacts", () => {
    // con floats: 0.1 + 0.2 = 0.30000000000000004
    expect(fromCents(toCents("0.1") + toCents("0.2"))).toBe("0.30");
  });

  it("rejects invalid amounts", () => {
    expect(() => toCents("12.345")).toThrow();
    expect(() => toCents("abc")).toThrow();
    expect(() => toCents("1e3")).toThrow();
  });
});

describe("isValidMoney", () => {
  it("accepts positive amounts with up to 2 decimals", () => {
    expect(isValidMoney("45")).toBe(true);
    expect(isValidMoney(" 45.50 ")).toBe(true);
    expect(isValidMoney("0")).toBe(false);
    expect(isValidMoney("-3")).toBe(false);
    expect(isValidMoney("4,50")).toBe(false);
  });
});

describe("formatMoney", () => {
  it("formats cents and strings identically", () => {
    expect(formatMoney("1250.50", "USD")).toBe(formatMoney(125050, "USD"));
    expect(formatMoney("1250.50", "USD")).toMatch(/1\.250,50/);
  });
});
