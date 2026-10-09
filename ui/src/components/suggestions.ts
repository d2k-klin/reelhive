import {z} from 'zod';

/** The only shape a `propose_suggestions` tool call may have. Anything else is never rendered or applied. */
export const SuggestionsSchema = z.object({
  suggestions: z
    .array(z.object({label: z.string().min(2).max(28), instruction: z.string().min(10).max(240)}))
    .min(3)
    .max(4),
});
export type Suggestion = z.infer<typeof SuggestionsSchema>['suggestions'][number];
