import { Component, computed, inject, signal } from '@angular/core';
import { NgTemplateOutlet } from '@angular/common';
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
  private readonly onboardingRunService = inject(OnboardingRunService);

  protected readonly viewModel = signal(initialGeneratePlanViewModel);
  protected readonly submitted = signal(false);

  protected readonly employmentTypes: SelectOption[] = [
    { label: 'Full-time', value: 'Full-time' },
    { label: 'Part-time', value: 'Part-time' },
    { label: 'Contractor', value: 'Contractor' },
    { label: 'Internship', value: 'Internship' },
  ];

  protected readonly workModes: SelectOption[] = [
    { label: 'Remote', value: 'Remote' },
    { label: 'Hybrid', value: 'Hybrid' },
    { label: 'On-site', value: 'On-site' },
  ];

  protected readonly seniorityLevels: SelectOption[] = [
    { label: 'Junior', value: 'Junior' },
    { label: 'Mid-level', value: 'Mid-level' },
    { label: 'Senior', value: 'Senior' },
    { label: 'Lead', value: 'Lead' },
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
    switch (this.viewModel().state) {
      case 'running':
        return 'Generating onboarding plan...';
      case 'done':
        return 'Onboarding plan generated for human review.';
      case 'error':
        return 'Could not generate onboarding plan. Review the form and try again.';
      case 'idle':
      default:
        return 'Ready to generate an onboarding plan.';
    }
  });

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

        this.onboardingRunService.getRunStatus(runId).subscribe({
          next: (response) => {
            if (response.status === 'done' && response.result) {
              this.viewModel.update((current) =>
                transitionGeneratePlan(current, {
                  type: 'RUN_DONE',
                  result: response.result!,
                }),
              );
              return;
            }

            this.viewModel.update((current) =>
              transitionGeneratePlan(current, {
                type: 'RUN_FAILED',
                message: response.errorMessage ?? response.message,
              }),
            );
          },
          error: () => {
            this.viewModel.update((current) =>
              transitionGeneratePlan(current, {
                type: 'RUN_FAILED',
                message: 'Falha inesperada ao consultar o status do run.',
              }),
            );
          },
        });
      },
      error: () => {
        this.viewModel.update((current) =>
          transitionGeneratePlan(current, {
            type: 'RUN_FAILED',
            message: 'Falha inesperada ao iniciar o run.',
          }),
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
