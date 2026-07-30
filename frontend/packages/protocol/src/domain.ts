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
