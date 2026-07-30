#!/usr/bin/env node
import { Command } from "commander";
import { CLI_VERSION } from "./version.js";

const program = new Command();

program
  .name("sagiha-mock")
  .description("SAGIHA mock-phase CLI cockpit — drives scripted runs against @sagiha/mock-engine.")
  .version(CLI_VERSION, "--version", "output the current version");

program.parse(process.argv);
