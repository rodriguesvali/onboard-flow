import { initialGeneratePlanViewModel, transitionGeneratePlan } from './generate-plan.state';
import { OnboardingPlanResult } from './onboarding-run.models';

describe('transitionGeneratePlan', () => {
  const result: OnboardingPlanResult = {
    employeeProfile: {
      fullName: 'Ana Silva',
      role: 'Engenheira de Software',
      department: 'Engenharia',
      directManager: 'Joaquim',
      startDate: '2026-06-15',
      workMode: 'Remoto',
    },
    executiveSummary: 'Resumo.',
    requiredDocuments: [],
    itChecklist: [],
    trainingPath: [],
    initialAgenda: [],
    communications: [],
    pendingActions: [],
    riskFlags: [],
    status: 'ready_for_review',
    nextRecommendedActions: [],
  };

  it('moves from idle to running when run is clicked', () => {
    const next = transitionGeneratePlan(initialGeneratePlanViewModel, { type: 'RUN_CLICKED' });

    expect(next.state).toBe('running');
  });

  it('stores the run id and moves to done with a result', () => {
    const running = transitionGeneratePlan(initialGeneratePlanViewModel, { type: 'RUN_CLICKED' });
    const started = transitionGeneratePlan(running, {
      type: 'RUN_STARTED',
      runId: 'mock-run-1',
    });
    const done = transitionGeneratePlan(started, {
      type: 'RUN_DONE',
      result,
    });

    expect(done.state).toBe('done');
    expect(done.runId).toBe('mock-run-1');
    expect(done.result).toBe(result);
  });

  it('replaces an existing result when a refinement returns an updated plan', () => {
    const running = transitionGeneratePlan(initialGeneratePlanViewModel, { type: 'RUN_CLICKED' });
    const started = transitionGeneratePlan(running, {
      type: 'RUN_STARTED',
      runId: 'mock-run-1',
    });
    const done = transitionGeneratePlan(started, {
      type: 'RUN_DONE',
      result,
    });
    const refinedResult: OnboardingPlanResult = {
      ...result,
      executiveSummary: 'Resumo refinado.',
      status: 'draft',
    };

    const refined = transitionGeneratePlan(done, {
      type: 'RUN_DONE',
      result: refinedResult,
    });

    expect(refined.state).toBe('done');
    expect(refined.runId).toBe('mock-run-1');
    expect(refined.result).toBe(refinedResult);
  });

  it('ignores invalid done transitions', () => {
    const next = transitionGeneratePlan(initialGeneratePlanViewModel, {
      type: 'RUN_DONE',
      result,
    });

    expect(next).toBe(initialGeneratePlanViewModel);
  });

  it('resets terminal states to idle', () => {
    const running = transitionGeneratePlan(initialGeneratePlanViewModel, { type: 'RUN_CLICKED' });
    const error = transitionGeneratePlan(running, {
      type: 'RUN_FAILED',
      message: 'Erro',
    });
    const reset = transitionGeneratePlan(error, { type: 'RESET_CLICKED' });

    expect(reset).toEqual(initialGeneratePlanViewModel);
  });
});
