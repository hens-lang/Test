// Warm-up-schema (§7b): week 1: 10/dag, week 2: 20, week 3: 35, week 4: 50, daarna max.
// dailyCap volgt dit schema automatisch; absolute bovengrens (maxDailyCap, default 50,
// tot 100 alleen door ADMIN te verhogen) wordt altijd gerespecteerd.

export const WARMUP_WEEKS = [10, 20, 35, 50];
export const DEFAULT_MAX_CAP = 50;
export const ABSOLUTE_MAX_CAP = 100;

/** Cap voor een gegeven warm-up-dag (dag 0 = eerste dag). */
export function warmupCapForDay(warmupDay: number, maxDailyCap: number = DEFAULT_MAX_CAP): number {
  const week = Math.floor(Math.max(0, warmupDay) / 7);
  const scheduled = week < WARMUP_WEEKS.length ? WARMUP_WEEKS[week] : WARMUP_WEEKS[WARMUP_WEEKS.length - 1];
  return Math.min(scheduled, clampMaxCap(maxDailyCap));
}

export function clampMaxCap(requested: number): number {
  return Math.max(1, Math.min(requested, ABSOLUTE_MAX_CAP));
}

/** Is de warm-up voltooid (4 weken doorlopen)? */
export function isWarmupComplete(warmupDay: number): boolean {
  return warmupDay >= WARMUP_WEEKS.length * 7;
}

/**
 * Dagelijkse stap: verhoogt warmupDay en herberekent dailyCap.
 * Puur — de dagelijkse job past het resultaat toe op de database.
 */
export function advanceWarmup(state: { warmupDay: number; maxDailyCap: number }): {
  warmupDay: number;
  dailyCap: number;
  completed: boolean;
} {
  const warmupDay = state.warmupDay + 1;
  return {
    warmupDay,
    dailyCap: warmupCapForDay(warmupDay, state.maxDailyCap),
    completed: isWarmupComplete(warmupDay),
  };
}
