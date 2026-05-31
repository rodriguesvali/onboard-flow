import { TestBed } from '@angular/core/testing';
import { firstValueFrom } from 'rxjs';

import { EmployeeOnboardingInput } from './onboarding-run.models';
import { OnboardingRunService } from './onboarding-run.service';

describe('OnboardingRunService', () => {
  let service: OnboardingRunService;

  const input: EmployeeOnboardingInput = {
    fullName: 'Ana Silva',
    email: 'ana.silva@example.com',
    role: 'Software Engineer',
    department: 'Engineering',
    directManager: 'Joaquim',
    startDate: '2026-06-15',
    employmentType: 'Full-time',
    workMode: 'Remote',
  };

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(OnboardingRunService);
  });

  it('returns a mocked running response when starting a run', async () => {
    const response = await firstValueFrom(service.startRun(input));

    expect(response.status).toBe('running');
    expect(response.runId).toContain('mock-run-');
  });

  it('returns a mocked onboarding plan for a known run', async () => {
    const startResponse = await firstValueFrom(service.startRun(input));
    const statusResponse = await firstValueFrom(service.getRunStatus(startResponse.runId));

    expect(statusResponse.status).toBe('done');
    expect(statusResponse.result?.employeeProfile.fullName).toBe('Ana Silva');
    expect(statusResponse.result?.communications.every((draft) => draft.draft)).toBe(true);
  });
});
