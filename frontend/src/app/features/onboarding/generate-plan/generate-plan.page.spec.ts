import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';

import { GeneratePlanPage } from './generate-plan.page';
import { OnboardingRunService } from './onboarding-run.service';

describe('GeneratePlanPage', () => {
  const onboardingRunService = {
    startRun: vi.fn(),
    getRunStatus: vi.fn(),
  };

  beforeEach(async () => {
    onboardingRunService.startRun.mockReturnValue(of({ runId: 'mock-run-1', status: 'running' }));
    onboardingRunService.getRunStatus.mockReturnValue(
      of({
        runId: 'mock-run-1',
        status: 'done',
        message: 'Plano gerado.',
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
          status: 'ready_for_review',
          nextRecommendedActions: [],
        },
      }),
    );

    await TestBed.configureTestingModule({
      imports: [GeneratePlanPage],
      providers: [{ provide: OnboardingRunService, useValue: onboardingRunService }],
    }).compileComponents();
  });

  afterEach(() => {
    onboardingRunService.startRun.mockClear();
    onboardingRunService.getRunStatus.mockClear();
  });

  it('renders the idle status banner', () => {
    const fixture = TestBed.createComponent(GeneratePlanPage);
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.textContent).toContain('Pronto para gerar um plano de onboarding.');
  });

  it('does not start a run when required fields are missing', () => {
    const fixture = TestBed.createComponent(GeneratePlanPage);
    fixture.detectChanges();

    const form = fixture.nativeElement.querySelector('form') as HTMLFormElement;
    form.dispatchEvent(new Event('submit'));
    fixture.detectChanges();

    expect(onboardingRunService.startRun).not.toHaveBeenCalled();
    expect(fixture.nativeElement.textContent).toContain('Informe o nome completo.');
  });

  it('shows the results view after a mocked successful run', async () => {
    const fixture = TestBed.createComponent(GeneratePlanPage);
    fixture.detectChanges();

    const component = fixture.componentInstance as unknown as {
      form: {
        setValue(value: Record<string, string | Date | null>): void;
      };
      run(): void;
    };

    component.form.setValue({
      fullName: 'Ana Silva',
      email: 'ana.silva@example.com',
      role: 'Engenheira de Software',
      department: 'Engenharia',
      directManager: 'Joaquim',
      startDate: new Date('2026-06-15T00:00:00'),
      employmentType: 'Tempo integral',
      workMode: 'Remoto',
      seniority: '',
      location: '',
      contractRegion: '',
      preferredLanguage: '',
      equipmentNeeds: '',
      specialAccessNotes: '',
    });
    component.run();
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();

    expect(onboardingRunService.startRun).toHaveBeenCalledOnce();
    expect(onboardingRunService.getRunStatus).toHaveBeenCalledWith('mock-run-1');
    expect(fixture.nativeElement.textContent).toContain(
      'Plano de onboarding gerado para revisao humana.',
    );
    expect(fixture.nativeElement.textContent).toContain('Ana Silva');
  });
});
