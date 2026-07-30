import { describe, expect, it } from "vitest";

describe("@sagiha/protocol scaffold", () => {
  it("exists and is importable", async () => {
    const mod = await import("./index.js");
    expect(mod).toBeDefined();
  });
});
