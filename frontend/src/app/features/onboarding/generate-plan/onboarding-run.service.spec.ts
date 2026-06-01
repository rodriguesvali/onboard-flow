import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { EmployeeOnboardingInput } from './onboarding-run.models';
import { ONBOARDING_API_BASE_URL, OnboardingRunService } from './onboarding-run.service';

describe('OnboardingRunService', () => {
  let service: OnboardingRunService;
  let http: HttpTestingController;

  const input: EmployeeOnboardingInput = {
    fullName: 'Ana Silva',
    email: 'ana.silva@example.com',
    role: 'Engenheira de Software',
    department: 'Engenharia',
    directManager: 'Joaquim',
    startDate: '2026-06-15',
    employmentType: 'Tempo integral',
    workMode: 'Remoto',
  };

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ONBOARDING_API_BASE_URL, useValue: 'http://api.test' },
      ],
    });
    service = TestBed.inject(OnboardingRunService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    http.verify();
  });

  it('starts a backend run through the generate endpoint', () => {
    let responseRunId = '';

    service.startRun(input).subscribe((response) => {
      responseRunId = response.runId;
    });

    const request = http.expectOne('http://api.test/api/onboarding/generate');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual(input);
    request.flush({ runId: 'run_1', status: 'running' });

    expect(responseRunId).toBe('run_1');
  });

  it('gets backend run status', () => {
    let status = '';

    service.getRunStatus('run_1').subscribe((response) => {
      status = response.status;
    });

    const request = http.expectOne('http://api.test/api/onboarding/runs/run_1');
    expect(request.request.method).toBe('GET');
    request.flush({
      runId: 'run_1',
      status: 'done',
      message: 'Plano gerado.',
      result: null,
    });

    expect(status).toBe('done');
  });

  it('submits a refinement instruction to the backend', () => {
    let revisionNumber = 0;

    service.refineRun('run_1', 'Revisar prazos.').subscribe((response) => {
      revisionNumber = response.revisionNumber;
    });

    const request = http.expectOne('http://api.test/api/onboarding/runs/run_1/refine');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({
      instruction: 'Revisar prazos.',
      planVersion: 1,
    });
    request.flush({
      runId: 'run_1',
      status: 'done',
      revisionId: 'rev_1',
      revisionNumber: 2,
      result: {
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
        status: 'draft',
        nextRecommendedActions: [],
      },
      markdown: '',
      validationResult: { status: 'complete', issues: [] },
    });

    expect(revisionNumber).toBe(2);
  });
});
