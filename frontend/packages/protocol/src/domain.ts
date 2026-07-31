/**
 * Field-exact TS/Zod mirror of the backend's frozen domain models. Grown scenario-by-scenario,
 * per docs/frontend/roadmap.md Phase 0 — do not add fields ahead of the scenario that needs them.
 * Source of truth: src/sagiha/domain/{control,work,identity}.py. No renaming for "nicer" TS casing.
 */
import { z } from "zod";

// --- identity.py ---

export const StepIdSchema = z.object({
  run_id: z.string(),
  branch_id: z.string(),
  seq: z.number().int(),
  parent: z.string().nullable().optional(),
});
export type StepId = z.infer<typeof StepIdSchema>;

// --- control.py ---

export const TaskStatusSchema = z.enum([
  "submitted",
  "working",
  "input-required",
  "auth-required",
  "completed",
  "failed",
  "canceled",
]);
export type TaskStatus = z.infer<typeof TaskStatusSchema>;

export const RunContextSchema = z.object({
  run_id: z.string(),
  autonomy_level: z.enum(["interactive", "hybrid", "autonomous", "scheduled"]),
  workspace_root: z.string(),
  budget_remaining_usd: z.number(),
});
export type RunContext = z.infer<typeof RunContextSchema>;

export const FreezeReasonSchema = z.enum(["budget", "failover", "interrupt", "checkpoint"]);
export type FreezeReason = z.infer<typeof FreezeReasonSchema>;

export const FrozenRunStateSchema = z.object({
  run_id: z.string(),
  task_id: z.string(),
  autonomy_level: z.enum(["interactive", "hybrid", "autonomous", "scheduled"]),
  workspace_root: z.string(),
  budget_remaining_usd: z.number(),
  worktree_ref: z.string().nullable().optional(),
  base_commit: z.string().nullable().optional(),
  next_seq: z.number().int().default(1),
  plan: z.array(z.string()).default([]),
  open_files: z.array(z.string()).default([]),
  tainted: z.boolean().default(false),
  frozen_at: z.string(),
  reason: FreezeReasonSchema.default("checkpoint"),
});
export type FrozenRunState = z.infer<typeof FrozenRunStateSchema>;

// --- work.py ---

export const AcceptanceCriterionSchema = z.object({
  description: z.string(),
  check: z.string(),
  required: z.boolean().default(true),
});
export type AcceptanceCriterion = z.infer<typeof AcceptanceCriterionSchema>;

export const TaskSpecSchema = z.object({
  task_id: z.string(),
  revision: z.number().int().default(0),
  goal: z.string(),
  acceptance: z.array(AcceptanceCriterionSchema),
  profile: z.string().default("coding"),
  parent_task_id: z.string().nullable().optional(),
  status: TaskStatusSchema.default("submitted"),
});
export type TaskSpec = z.infer<typeof TaskSpecSchema>;

export const CostSummarySchema = z.object({
  usd: z.number(),
  input_tokens: z.number().int(),
  output_tokens: z.number().int(),
  wall_clock_s: z.number(),
  model_calls: z.number().int(),
});
export type CostSummary = z.infer<typeof CostSummarySchema>;

export const TokenUsageSchema = z.object({
  prompt_tokens: z.number().int(),
  completion_tokens: z.number().int(),
  total_tokens: z.number().int(),
  cost_usd: z.number().optional(),
});
export type TokenUsage = z.infer<typeof TokenUsageSchema>;

export const CriterionResultSchema = z.object({
  description: z.string(),
  check: z.string(),
  passed: z.boolean(),
  required: z.boolean(),
  output: z.string().default(""),
  duration_ms: z.number().default(0.0),
});
export type CriterionResult = z.infer<typeof CriterionResultSchema>;

export const GateReportSchema = z.object({
  criteria: z.array(CriterionResultSchema),
  no_new_suppressions: z.boolean().nullable().optional(),
  tests_unmodified: z.boolean().nullable().optional(),
  coverage_not_decreased: z.boolean().nullable().optional(),
  diff_within_bounds: z.boolean().nullable().optional(),
  required_gates: z
    .array(z.string())
    .default(["no_new_suppressions", "tests_unmodified", "diff_within_bounds"]),
  admitted: z.boolean().default(false),
});
export type GateReport = z.infer<typeof GateReportSchema>;

export const TrajectoryStepSchema = z.object({
  step_id: StepIdSchema,
  kind: z.string(),
  timestamp: z.string(),
  tool_name: z.string().optional(),
  arguments: z.record(z.unknown()).optional(),
  output: z.unknown().optional(),
  error: z.string().optional(),
  token_usage: TokenUsageSchema.optional(),
  tainted: z.boolean().optional(),
});
export type TrajectoryStep = z.infer<typeof TrajectoryStepSchema>;
