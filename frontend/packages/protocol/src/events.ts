/**
 * Field-exact mirror of src/sagiha/domain/events.py's Event base and (as of FE-2) exactly one
 * concrete event, RunStarted. Grown event-by-event as later sprints need them — see
 * docs/sprints/sprint-fe-{3,4,5}.md for the rest of the taxonomy.
 */
import { z } from "zod";
import { RunContextSchema, TaskSpecSchema } from "./domain.js";
import { StepIdSchema } from "./domain.js";

export const EventBaseSchema = z.object({
  event: z.string(),
  schema_version: z.number().int().default(1),
  run_id: z.string(),
  step_id: StepIdSchema.nullable().optional(),
  timestamp: z.coerce.date(),
});

export const RunStartedSchema = EventBaseSchema.extend({
  event: z.literal("run.started"),
  task: TaskSpecSchema,
  run_context: RunContextSchema,
  profile: z.string(),
  extension_manifest: z.array(z.string()).default([]),
});
export type RunStarted = z.infer<typeof RunStartedSchema>;

/** Discriminated union of every event the frontend can receive. Grows sprint by sprint. */
export const SagihaEventSchema = z.discriminatedUnion("event", [RunStartedSchema]);
export type SagihaEvent = z.infer<typeof SagihaEventSchema>;
