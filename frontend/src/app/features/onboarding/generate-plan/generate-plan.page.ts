import { DOCUMENT, NgTemplateOutlet } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { DatePickerModule } from 'primeng/datepicker';
import { InputTextModule } from 'primeng/inputtext';
import { MessageModule } from 'primeng/message';
import { ProgressBarModule } from 'primeng/progressbar';
import { SelectModule } from 'primeng/select';
import { TagModule } from 'primeng/tag';
import { TextareaModule } from 'primeng/textarea';

import { initialGeneratePlanViewModel, transitionGeneratePlan } from './generate-plan.state';
import { EmployeeOnboardingInput, ResultItem } from './onboarding-run.models';
import { OnboardingRunService } from './onboarding-run.service';

interface SelectOption {
  label: string;
  value: string;
}

type ThemeMode = 'light' | 'dark';
type ReviewDecision = 'pending' | 'approved' | 'changes_requested';

type GeneratePlanForm = FormGroup<{
  fullName: FormControl<string>;
  email: FormControl<string>;
  role: FormControl<string>;
  department: FormControl<string>;
  directManager: FormControl<string>;
  startDate: FormControl<Date | null>;
  employmentType: FormControl<string>;
  workMode: FormControl<string>;
  seniority: FormControl<string>;
  location: FormControl<string>;
  contractRegion: FormControl<string>;
  preferredLanguage: FormControl<string>;
  equipmentNeeds: FormControl<string>;
  specialAccessNotes: FormControl<string>;
}>;

@Component({
  selector: 'app-generate-plan-page',
  imports: [
    ReactiveFormsModule,
    NgTemplateOutlet,
    ButtonModule,
    CardModule,
    DatePickerModule,
    InputTextModule,
    MessageModule,
    ProgressBarModule,
    SelectModule,
    TagModule,
    TextareaModule,
  ],
  templateUrl: './generate-plan.page.html',
  styleUrl: './generate-plan.page.scss',
})
export class GeneratePlanPage {
  private readonly document = inject(DOCUMENT);
  private readonly onboardingRunService = inject(OnboardingRunService);

  protected readonly viewModel = signal(initialGeneratePlanViewModel);
  protected readonly submitted = signal(false);
  protected readonly themeMode = signal<ThemeMode>(this.readInitialThemeMode());
  protected readonly reviewDecision = signal<ReviewDecision>('pending');
  protected readonly reviewFeedbackOpen = signal(false);
  protected readonly reviewFeedbackSubmitted = signal(false);
  protected readonly refinementRunning = signal(false);
  protected readonly refinementError = signal<string | null>(null);
  protected readonly reviewFeedback = new FormControl('', {
    nonNullable: true,
    validators: [Validators.required],
  });
  protected readonly isDarkTheme = computed(() => this.themeMode() === 'dark');

  protected readonly employmentTypes: SelectOption[] = [
    { label: 'Tempo integral', value: 'Tempo integral' },
    { label: 'Meio periodo', value: 'Meio periodo' },
    { label: 'Prestador de servico', value: 'Prestador de servico' },
    { label: 'Estagio', value: 'Estagio' },
  ];

  protected readonly workModes: SelectOption[] = [
    { label: 'Remoto', value: 'Remoto' },
    { label: 'Hibrido', value: 'Hibrido' },
    { label: 'Presencial', value: 'Presencial' },
  ];

  protected readonly seniorityLevels: SelectOption[] = [
    { label: 'Junior', value: 'Junior' },
    { label: 'Pleno', value: 'Pleno' },
    { label: 'Senior', value: 'Senior' },
    { label: 'Lider', value: 'Lider' },
  ];

  protected readonly form: GeneratePlanForm = new FormGroup({
    fullName: new FormControl('', { nonNullable: true, validators: [Validators.required] }),
    email: new FormControl('', {
      nonNullable: true,
      validators: [Validators.required, Validators.email],
    }),
    role: new FormControl('', { nonNullable: true, validators: [Validators.required] }),
    department: new FormControl('', { nonNullable: true, validators: [Validators.required] }),
    directManager: new FormControl('', { nonNullable: true, validators: [Validators.required] }),
    startDate: new FormControl<Date | null>(null, { validators: [Validators.required] }),
    employmentType: new FormControl('', {
      nonNullable: true,
      validators: [Validators.required],
    }),
    workMode: new FormControl('', { nonNullable: true, validators: [Validators.required] }),
    seniority: new FormControl('', { nonNullable: true }),
    location: new FormControl('', { nonNullable: true }),
    contractRegion: new FormControl('', { nonNullable: true }),
    preferredLanguage: new FormControl('', { nonNullable: true }),
    equipmentNeeds: new FormControl('', { nonNullable: true }),
    specialAccessNotes: new FormControl('', { nonNullable: true }),
  });

  protected readonly isRunning = computed(() => this.viewModel().state === 'running');
  protected readonly result = computed(() => this.viewModel().result);
  protected readonly statusSeverity = computed(() => {
    if (this.viewModel().state === 'done' && this.reviewDecision() === 'changes_requested') {
      return 'warn';
    }

    switch (this.viewModel().state) {
      case 'done':
        return 'success';
      case 'error':
        return 'error';
      default:
        return 'info';
    }
  });
  protected readonly statusText = computed(() => {
    if (this.viewModel().state === 'done') {
      switch (this.reviewDecision()) {
        case 'approved':
          return 'Plano aprovado nesta sessao de revisao. Nenhuma comunicacao foi enviada.';
        case 'changes_requested':
          return 'Solicitacao de ajustes registrada nesta sessao de revisao.';
        case 'pending':
        default:
          return 'Plano de onboarding gerado para revisao humana.';
      }
    }

    switch (this.viewModel().state) {
      case 'running':
        return 'Gerando plano de onboarding...';
      case 'error':
        return (
          'Nao foi possivel gerar o plano de onboarding. ' +
          'Revise o formulario e tente novamente.'
        );
      case 'idle':
      default:
        return 'Pronto para gerar um plano de onboarding.';
    }
  });

  constructor() {
    this.applyThemeMode(this.themeMode());
  }

  protected setThemeMode(mode: ThemeMode): void {
    this.themeMode.set(mode);
    this.applyThemeMode(mode);
  }

  protected run(): void {
    this.submitted.set(true);

    if (this.form.invalid || this.isRunning()) {
      this.form.markAllAsTouched();
      return;
    }

    this.viewModel.update((current) => transitionGeneratePlan(current, { type: 'RUN_CLICKED' }));

    this.onboardingRunService.startRun(this.toInput()).subscribe({
      next: ({ runId }) => {
        this.viewModel.update((current) =>
          transitionGeneratePlan(current, { type: 'RUN_STARTED', runId }),
        );

        this.onboardingRunService.pollRunStatus(runId).subscribe({
          next: (response) => {
            if (response.status === 'done' && response.result) {
              this.viewModel.update((current) =>
                transitionGeneratePlan(current, {
                  type: 'RUN_DONE',
                  result: response.result!,
                }),
              );
              this.resetReviewState();
              return;
            }

            this.viewModel.update((current) =>
              transitionGeneratePlan(current, {
                type: 'RUN_FAILED',
                message: response.errorMessage ?? response.message,
              }),
            );
          },
          error: (error: unknown) => {
            this.viewModel.update((current) =>
              transitionGeneratePlan(current, {
                type: 'RUN_FAILED',
                message: apiErrorMessage(error, 'Falha inesperada ao consultar o status do run.'),
              }),
            );
          },
        });
      },
      error: (error: unknown) => {
        this.viewModel.update((current) =>
          transitionGeneratePlan(current, {
            type: 'RUN_FAILED',
            message: apiErrorMessage(error, 'Falha inesperada ao iniciar o run.'),
          }),
        );
      },
    });
  }

  protected approvePlan(): void {
    this.reviewDecision.set('approved');
    this.reviewFeedbackOpen.set(false);
    this.reviewFeedbackSubmitted.set(false);
    this.reviewFeedback.reset('');
  }

  protected openChangeRequest(): void {
    this.reviewDecision.set('pending');
    this.reviewFeedbackOpen.set(true);
    this.reviewFeedbackSubmitted.set(false);
    this.refinementError.set(null);
  }

  protected submitChangeRequest(): void {
    this.reviewFeedbackSubmitted.set(true);
    this.refinementError.set(null);

    if (this.reviewFeedback.invalid) {
      this.reviewFeedback.markAsTouched();
      return;
    }

    const runId = this.viewModel().runId;
    if (!runId) {
      this.reviewDecision.set('changes_requested');
      this.reviewFeedbackOpen.set(false);
      return;
    }

    this.refinementRunning.set(true);
    this.onboardingRunService.refineRun(runId, this.reviewFeedback.value).subscribe({
      next: (response) => {
        this.viewModel.update((current) =>
          transitionGeneratePlan(current, {
            type: 'RUN_DONE',
            result: response.result,
          }),
        );
        this.reviewDecision.set('changes_requested');
        this.reviewFeedbackOpen.set(false);
        this.refinementRunning.set(false);
      },
      error: (error: unknown) => {
        this.refinementRunning.set(false);
        this.refinementError.set(
          apiErrorMessage(error, 'Nao foi possivel solicitar ajustes no backend.'),
        );
      },
    });
  }

  protected reset(): void {
    this.form.reset({
      fullName: '',
      email: '',
      role: '',
      department: '',
      directManager: '',
      startDate: null,
      employmentType: '',
      workMode: '',
      seniority: '',
      location: '',
      contractRegion: '',
      preferredLanguage: '',
      equipmentNeeds: '',
      specialAccessNotes: '',
    });
    this.submitted.set(false);
    this.resetReviewState();
    this.viewModel.update((current) => transitionGeneratePlan(current, { type: 'RESET_CLICKED' }));
  }

  protected showRequiredError(controlName: keyof GeneratePlanForm['controls']): boolean {
    const control = this.form.controls[controlName];
    return control.hasError('required') && (control.touched || this.submitted());
  }

  protected showEmailError(): boolean {
    const control = this.form.controls.email;
    return control.hasError('email') && (control.touched || this.submitted());
  }

  protected statusLabel(item: ResultItem): string {
    const labels: Record<ResultItem['status'], string> = {
      pending: 'Pendente',
      recommended: 'Recomendado',
      blocked: 'Bloqueado',
      done: 'Concluido',
    };

    return labels[item.status];
  }

  protected planStatusLabel(status: 'draft' | 'ready_for_review' | 'incomplete'): string {
    const labels: Record<'draft' | 'ready_for_review' | 'incomplete', string> = {
      draft: 'Rascunho',
      ready_for_review: 'Pronto para revisao',
      incomplete: 'Incompleto',
    };

    return labels[status];
  }

  protected audienceLabel(audience: 'collaborator' | 'manager' | 'it' | 'hr'): string {
    const labels: Record<'collaborator' | 'manager' | 'it' | 'hr', string> = {
      collaborator: 'Colaborador',
      manager: 'Gestor',
      it: 'TI',
      hr: 'RH',
    };

    return labels[audience];
  }

  protected showReviewFeedbackError(): boolean {
    return (
      this.reviewFeedback.hasError('required') &&
      (this.reviewFeedback.touched || this.reviewFeedbackSubmitted())
    );
  }

  protected statusSeverityFor(item: ResultItem): 'info' | 'success' | 'warn' | 'danger' {
    switch (item.status) {
      case 'done':
        return 'success';
      case 'blocked':
        return 'danger';
      case 'pending':
        return 'warn';
      case 'recommended':
      default:
        return 'info';
    }
  }

  private toInput(): EmployeeOnboardingInput {
    const value = this.form.getRawValue();

    return {
      fullName: value.fullName.trim(),
      email: value.email.trim(),
      role: value.role.trim(),
      department: value.department.trim(),
      directManager: value.directManager.trim(),
      startDate: formatDate(value.startDate),
      employmentType: value.employmentType,
      workMode: value.workMode,
      seniority: optional(value.seniority),
      location: optional(value.location),
      contractRegion: optional(value.contractRegion),
      preferredLanguage: optional(value.preferredLanguage),
      equipmentNeeds: optional(value.equipmentNeeds),
      specialAccessNotes: optional(value.specialAccessNotes),
    };
  }

  private resetReviewState(): void {
    this.reviewDecision.set('pending');
    this.reviewFeedbackOpen.set(false);
    this.reviewFeedbackSubmitted.set(false);
    this.refinementRunning.set(false);
    this.refinementError.set(null);
    this.reviewFeedback.reset('');
  }

  private readInitialThemeMode(): ThemeMode {
    return localStorage.getItem('onboardflow-theme') === 'dark' ? 'dark' : 'light';
  }

  private applyThemeMode(mode: ThemeMode): void {
    const root = this.document.documentElement;
    root.classList.toggle('app-dark', mode === 'dark');
    root.dataset['theme'] = mode;
    localStorage.setItem('onboardflow-theme', mode);
  }
}

function optional(value: string): string | undefined {
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : undefined;
}

function formatDate(value: Date | null): string {
  if (!value) {
    return '';
  }

  return value.toISOString().slice(0, 10);
}

function apiErrorMessage(error: unknown, fallback: string): string {
  if (isHttpErrorWithMessage(error)) {
    if (typeof error.error?.detail === 'string') {
      return error.error.detail;
    }

    if (typeof error.error?.errorMessage === 'string') {
      return error.error.errorMessage;
    }

    if (typeof error.message === 'string' && error.message.length > 0) {
      return error.message;
    }
  }

  return fallback;
}

function isHttpErrorWithMessage(error: unknown): error is {
  error?: { detail?: unknown; errorMessage?: unknown };
  message?: unknown;
} {
  return typeof error === 'object' && error !== null;
}
