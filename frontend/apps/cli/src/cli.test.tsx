import { execFileSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const dirname = path.dirname(fileURLToPath(import.meta.url));
const distEntry = path.resolve(dirname, "../dist/cli.js");

describe("sagiha-mock CLI", () => {
  it("prints a version for --version", () => {
    const out = execFileSync("node", [distEntry, "--version"], { encoding: "utf8" });
    expect(out.trim()).toMatch(/^\d+\.\d+\.\d+$/);
  });

  it("prints usage for --help", () => {
    const out = execFileSync("node", [distEntry, "--help"], { encoding: "utf8" });
    expect(out).toContain("sagiha-mock");
  });
});
