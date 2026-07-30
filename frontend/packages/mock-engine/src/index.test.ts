import { describe, expect, it } from "vitest";

describe("@sagiha/mock-engine scaffold", () => {
  it("exists and is importable", async () => {
    const mod = await import("./index.js");
    expect(mod).toBeDefined();
  });
});
