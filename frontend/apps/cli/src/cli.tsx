#!/usr/bin/env node
import { Command } from "commander";
import { render } from "ink";
import React from "react";
import { CLI_VERSION } from "./version.js";
import { CockpitView } from "./views/CockpitView.js";

const program = new Command();

program
  .name("sagiha-mock")
  .description("SAGIHA mock-phase CLI cockpit — drives scripted runs against @sagiha/mock-engine.")
  .version(CLI_VERSION, "--version", "output the current version")
  .action(() => {
    render(<CockpitView />);
  });

program.parse(process.argv);
