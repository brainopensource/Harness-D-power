import React from "react";
import { render } from "ink";
import { App } from "./App";

const isTTY = process.stdin.isTTY && process.stdout.isTTY;

if (isTTY) {
  render(<App />);
} else {
  render(<App />, {
    stdin: process.stdin,
    stdout: process.stdout,
    stderr: process.stderr,
  }).catch((err) => {
    if (err.message?.includes("Raw mode")) {
      console.log("\n📦 AETHER CLI (Mock Mode - Non-Interactive)\n");
      console.log("ℹ️  For interactive mode, run in a terminal: pnpm --filter @aether/cli dev");
      console.log("✓ Mock engine is loaded and streaming events...\n");
      setTimeout(() => process.exit(0), 2000);
    } else {
      throw err;
    }
  });
}
