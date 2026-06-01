import { OnboardingPlanResult } from './onboarding-run.models';

export type GeneratePlanState = 'idle' | 'running' | 'done' | 'error';

export type GeneratePlanEvent =
  | { type: 'RUN_CLICKED' }
  | { type: 'RUN_STARTED'; runId: string }
  | { type: 'RUN_DONE'; result: OnboardingPlanResult }
  | { type: 'RUN_FAILED'; message: string }
  | { type: 'RESET_CLICKED' };

export interface GeneratePlanViewModel {
  state: GeneratePlanState;
  runId: string | null;
  result: OnboardingPlanResult | null;
  errorMessage: string | null;
}

export const initialGeneratePlanViewModel: GeneratePlanViewModel = {
  state: 'idle',
  runId: null,
  result: null,
  errorMessage: null,
};

export function transitionGeneratePlan(
  current: GeneratePlanViewModel,
  event: GeneratePlanEvent,
): GeneratePlanViewModel {
  switch (event.type) {
    case 'RUN_CLICKED':
      if (current.state === 'idle' || current.state === 'error') {
        return {
          ...current,
          state: 'running',
          errorMessage: null,
        };
      }

      return current;

    case 'RUN_STARTED':
      if (current.state === 'running' || current.state === 'done') {
        return {
          ...current,
          runId: event.runId,
        };
      }

      return current;

    case 'RUN_DONE':
      if (current.state === 'running' || current.state === 'done') {
        return {
          state: 'done',
          runId: current.runId,
          result: event.result,
          errorMessage: null,
        };
      }

      return current;

    case 'RUN_FAILED':
      if (current.state === 'running') {
        return {
          ...current,
          state: 'error',
          errorMessage: event.message,
        };
      }

      return current;

    case 'RESET_CLICKED':
      if (current.state === 'idle' || current.state === 'error' || current.state === 'done') {
        return initialGeneratePlanViewModel;
      }

      return current;
  }
}
