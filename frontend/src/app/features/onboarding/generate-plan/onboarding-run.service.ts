import { Injectable } from '@angular/core';
import { delay, Observable, of } from 'rxjs';

import {
  EmployeeOnboardingInput,
  OnboardingPlanResult,
  RunStatusResponse,
  StartRunResponse,
} from './onboarding-run.models';

@Injectable({ providedIn: 'root' })
export class OnboardingRunService {
  private readonly runs = new Map<string, EmployeeOnboardingInput>();

  startRun(input: EmployeeOnboardingInput): Observable<StartRunResponse> {
    const runId = `mock-run-${Date.now()}`;
    this.runs.set(runId, input);

    return of({
      runId,
      status: 'running' as const,
    }).pipe(delay(400));
  }

  getRunStatus(runId: string): Observable<RunStatusResponse> {
    const input = this.runs.get(runId);

    if (!input) {
      return of({
        runId,
        status: 'error' as const,
        message: 'Could not generate onboarding plan. Review the form and try again.',
        errorMessage: 'Run mockado nao encontrado.',
      }).pipe(delay(300));
    }

    if (input.specialAccessNotes?.toLowerCase().includes('mock-error')) {
      return of({
        runId,
        status: 'error' as const,
        message: 'Could not generate onboarding plan. Review the form and try again.',
        errorMessage: 'Falha simulada do servico mockado.',
      }).pipe(delay(700));
    }

    return of({
      runId,
      status: 'done' as const,
      message: 'Plano de onboarding gerado para revisao.',
      result: buildMockResult(input),
    }).pipe(delay(900));
  }
}

function buildMockResult(input: EmployeeOnboardingInput): OnboardingPlanResult {
  return {
    employeeProfile: {
      fullName: input.fullName,
      role: input.role,
      department: input.department,
      directManager: input.directManager,
      startDate: input.startDate,
      workMode: input.workMode,
    },
    executiveSummary: `${input.fullName} precisa de um plano coordenado entre RH, gestor direto e TI para iniciar como ${input.role} em ${input.department}.`,
    requiredDocuments: [
      {
        title: 'Contrato e dados cadastrais revisados',
        ownerRole: 'RH',
        status: 'pending',
        rationale: 'Confirma dados basicos antes da data de inicio.',
      },
      {
        title: 'Politicas internas e termo de confidencialidade',
        ownerRole: 'RH',
        status: 'recommended',
        rationale: 'Entrega padrao para todos os novos colaboradores.',
      },
    ],
    itChecklist: [
      {
        title: 'Notebook, email corporativo e MFA',
        ownerRole: 'TI',
        status: 'pending',
        rationale: input.equipmentNeeds || 'Necessario para acesso inicial seguro.',
      },
      {
        title: `Acessos ao departamento ${input.department}`,
        ownerRole: 'TI',
        status: 'recommended',
        rationale: input.specialAccessNotes || 'Validar com gestor direto antes de provisionar.',
      },
    ],
    trainingPath: [
      {
        title: 'Boas-vindas institucionais',
        ownerRole: 'RH',
        status: 'recommended',
        rationale: 'Contextualiza cultura, processos e canais de suporte.',
      },
      {
        title: `Trilha inicial para ${input.role}`,
        ownerRole: 'Gestor direto',
        status: 'pending',
        rationale: 'Ajustar conteudo conforme senioridade e escopo do cargo.',
      },
    ],
    initialAgenda: [
      {
        title: 'Dia 1: recepcao, equipamentos e alinhamento com gestor',
        ownerRole: 'RH',
        status: 'recommended',
      },
      {
        title: 'Semana 1: reunioes com pares e revisao de objetivos iniciais',
        ownerRole: 'Gestor direto',
        status: 'recommended',
      },
    ],
    communications: [
      {
        audience: 'collaborator',
        subject: `Boas-vindas ao time de ${input.department}`,
        body: `Ola ${input.fullName}, preparamos um plano inicial para sua chegada. Revise as orientacoes com RH e ${input.directManager} no primeiro dia.`,
        draft: true,
      },
      {
        audience: 'manager',
        subject: `Preparacao para chegada de ${input.fullName}`,
        body: `Confirme agenda inicial, acessos necessarios e objetivos da primeira semana antes de ${input.startDate}.`,
        draft: true,
      },
    ],
    pendingActions: [
      {
        title: 'Validar acessos antes de qualquer provisionamento',
        ownerRole: 'Gestor direto',
        status: 'pending',
      },
      {
        title: 'Revisar mensagens draft antes de envio externo',
        ownerRole: 'RH',
        status: 'pending',
      },
    ],
    riskFlags: [
      {
        title: 'Dependencia de confirmacao de acessos',
        ownerRole: 'TI',
        status: input.specialAccessNotes ? 'recommended' : 'pending',
        rationale:
          'O MVP nao provisiona sistemas; apenas sinaliza a necessidade de revisao humana.',
      },
    ],
    status: 'ready_for_review',
    nextRecommendedActions: [
      'Revisar dados do colaborador e gestor direto.',
      'Confirmar checklist de TI antes da data de inicio.',
      'Aprovar ou ajustar comunicados draft antes de qualquer envio.',
    ],
  };
}
