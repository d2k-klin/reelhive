import type {Brief} from './api/client';

export const DRAFT_KEY = 'reelhive-draft';

/** Fill the brief form with an earlier production's brief; creating a video from it starts a new run. */
export function reuseBrief(brief: Brief | null | undefined): boolean {
  if (!brief) return false;
  if (localStorage.getItem(DRAFT_KEY) && !confirm("Replace your unsaved draft with this production's brief?")) return false;
  localStorage.setItem(DRAFT_KEY, JSON.stringify(brief));
  return true;
}
