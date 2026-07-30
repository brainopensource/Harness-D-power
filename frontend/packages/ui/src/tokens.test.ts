import { describe, expect, it } from "vitest";
import { chalkColor, motionDurationMs, spacing, statusGlyph, typeScale } from "./tokens.js";

describe("@sagiha/ui tokens", () => {
  it("exposes the full spacing scale", () => {
    expect(Object.keys(spacing)).toHaveLength(8);
  });

  it("exposes the full type scale", () => {
    expect(Object.keys(typeScale)).toHaveLength(6);
  });

  it("exposes all motion durations", () => {
    expect(motionDurationMs).toEqual({ micro: 100, standard: 200, emphasis: 320 });
  });

  it("maps every semantic color to a chalk color", () => {
    expect(chalkColor.success).toBe("green");
    expect(chalkColor.danger).toBe("red");
  });

  it("never signals status by color alone", () => {
    expect(statusGlyph.success).toBe("✓");
    expect(statusGlyph.failure).toBe("✗");
  });
});
