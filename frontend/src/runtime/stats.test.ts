import { describe, expect, it } from "vitest";
import { mean, stddev, successiveJitterMs } from "./stats";

describe("stats", () => {
  it("computes mean", () => {
    expect(mean([1, 2, 3])).toBe(2);
  });
  it("computes stddev", () => {
    expect(stddev([2, 4])).toBeGreaterThan(0);
  });
  it("computes successive jitter", () => {
    expect(successiveJitterMs([10, 12, 11])).toBeCloseTo(1.5, 5);
  });
});
