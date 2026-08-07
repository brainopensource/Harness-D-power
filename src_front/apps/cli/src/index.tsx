import React from "react";
import { render } from "ink";
import { App } from "./App";

const isTTY = Boolean(process.stdin?.isTTY) && Boolean(process.stdout?.isTTY);

if (isTTY) {
  render(<App />);
} else {
  // Non-interactive mode fallback
  console.log("\n📦 AETHER CLI (Mock Mode - Non-Interactive)\n");
  console.log("ℹ️  For interactive mode, run in a real terminal:\n   pnpm --filter @aether/cli dev\n");

  // Simulate some mock output
  console.log("🔄 Starting mock execution stream...");
  console.log("  • Budget allocated: $5.00");
  console.log("  • Topology: linear_repair_v1");
  console.log("  • Mode: Mock cassette playback");
  console.log("  • Status: CONNECTED ✓");
  console.log("\n✨ CLI bootstrap successful!\n");
  console.log("Commands: (p)lay, (s)tep, (c)assette, (q)uit\n");

  setTimeout(() => process.exit(0), 1000);
}
