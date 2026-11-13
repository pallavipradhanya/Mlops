import { describe, expect, it } from "vitest";
import { formatDetail } from "../lib/api";
import { label, num, pct, riskColor, shortHash } from "../lib/format";

describe("format helpers", () => {
  it("formats percentages and handles missing values", () => {
    expect(pct(0.8123)).toBe("81.2%");
    expect(pct(null)).toBe("—");
    expect(pct(Number.NaN)).toBe("—");
  });
  it("formats numbers", () => {
    expect(num(0.84221, 3)).toBe("0.842");
    expect(num(undefined)).toBe("—");
  });
  it("shortens hashes and labels", () => {
    expect(shortHash("abcdef1234567890")).toBe("abcdef12");
    expect(shortHash(null)).toBe("—");
    expect(label("roc_auc")).toBe("Roc Auc");
  });
  it("maps risk to colours", () => {
    expect(riskColor("high")).toContain("bad");
    expect(riskColor("low")).toContain("ok");
  });
});

describe("API error formatting", () => {
  it("passes strings through", () => expect(formatDetail("boom")).toBe("boom"));
  it("flattens FastAPI validation errors", () => {
    expect(formatDetail([{ loc: ["body", "tenure"], msg: "must be >= 0" }])).toBe("tenure: must be >= 0");
  });
});
