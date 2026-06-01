import { HttpClient } from '@angular/common/http';
import { Inject, Injectable, InjectionToken } from '@angular/core';
import { catchError, filter, Observable, switchMap, take, throwError, timeout, timer } from 'rxjs';

import {
  EmployeeOnboardingInput,
  RefinePlanResponse,
  RunStatusResponse,
  StartRunResponse,
} from './onboarding-run.models';

export const ONBOARDING_API_BASE_URL = new InjectionToken<string>('ONBOARDING_API_BASE_URL', {
  providedIn: 'root',
  factory: () => 'http://localhost:8000',
});

@Injectable({ providedIn: 'root' })
export class OnboardingRunService {
  private readonly pollIntervalMs = 2_000;
  private readonly pollTimeoutMs = 180_000;

  constructor(
    private readonly http: HttpClient,
    @Inject(ONBOARDING_API_BASE_URL) private readonly apiBaseUrl: string,
  ) {}

  startRun(input: EmployeeOnboardingInput): Observable<StartRunResponse> {
    return this.http.post<StartRunResponse>(this.url('/api/onboarding/generate'), input);
  }

  getRunStatus(runId: string): Observable<RunStatusResponse> {
    return this.http.get<RunStatusResponse>(this.url(`/api/onboarding/runs/${runId}`));
  }

  pollRunStatus(runId: string): Observable<RunStatusResponse> {
    return timer(0, this.pollIntervalMs).pipe(
      switchMap(() => this.getRunStatus(runId)),
      filter((response) => response.status !== 'running'),
      take(1),
      timeout({ first: this.pollTimeoutMs }),
      catchError((error) => throwError(() => error)),
    );
  }

  refineRun(runId: string, instruction: string, planVersion = 1): Observable<RefinePlanResponse> {
    return this.http.post<RefinePlanResponse>(this.url(`/api/onboarding/runs/${runId}/refine`), {
      instruction,
      planVersion,
    });
  }

  private url(path: string): string {
    return `${this.apiBaseUrl.replace(/\/$/, '')}${path}`;
  }
}
