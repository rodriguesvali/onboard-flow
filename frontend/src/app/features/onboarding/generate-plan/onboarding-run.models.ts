export interface EmployeeOnboardingInput {
  fullName: string;
  email: string;
  role: string;
  department: string;
  directManager: string;
  startDate: string;
  employmentType: string;
  workMode: string;
  seniority?: string;
  location?: string;
  contractRegion?: string;
  preferredLanguage?: string;
  equipmentNeeds?: string;
  specialAccessNotes?: string;
}

export interface StartRunResponse {
  runId: string;
  status: 'running';
}

export interface RunStatusResponse {
  runId: string;
  status: 'running' | 'done' | 'error';
  message: string;
  result?: OnboardingPlanResult;
  validationResult?: ValidationResult;
  agentActivity?: AgentAction[];
  dispatchReceipts?: DispatchReceipt[];
  errorMessage?: string;
}

export interface RefinePlanResponse {
  runId: string;
  status: 'done' | 'error';
  revisionId: string;
  revisionNumber: number;
  result: OnboardingPlanResult;
  markdown: string;
  validationResult: ValidationResult;
}

export interface DispatchRunResponse {
  runId: string;
  revisionNumber: number;
  status: 'running' | 'done' | 'error';
  simulated: true;
  dispatchSummary: DispatchSummary;
  receipts: DispatchReceipt[];
  agentActivity: AgentAction[];
}

export interface OnboardingPlanResult {
  employeeProfile: {
    fullName: string;
    role: string;
    department: string;
    directManager: string;
    startDate: string;
    workMode: string;
  };
  executiveSummary: string;
  requiredDocuments: ResultItem[];
  itChecklist: ResultItem[];
  trainingPath: ResultItem[];
  initialAgenda: ResultItem[];
  communications: CommunicationDraft[];
  pendingActions: ResultItem[];
  riskFlags: ResultItem[];
  status: 'draft' | 'ready_for_review' | 'incomplete';
  nextRecommendedActions: string[];
}

export interface ResultItem {
  title: string;
  ownerRole: string;
  status: 'pending' | 'recommended' | 'blocked' | 'done';
  rationale?: string;
}

export interface CommunicationDraft {
  audience: 'collaborator' | 'manager' | 'it' | 'hr';
  subject: string;
  body: string;
  draft: true;
}

export interface ValidationResult {
  status: 'complete' | 'draft_usable' | 'unusable';
  issues: ValidationIssue[];
}

export interface ValidationIssue {
  field: string;
  message: string;
  severity: 'error' | 'warning';
}

export interface AgentAction {
  actionId: string;
  runId: string;
  actorId: string;
  actorName: string;
  actionType: string;
  taskId?: string | null;
  agentName?: string | null;
  status: string;
  summary: string;
  modelProvider?: string | null;
  modelName?: string | null;
  modelProfile?: string | null;
  retryCount: number;
  validationResult?: string | null;
  createdAt: string;
}

export interface DispatchSummary {
  total: number;
  email: number;
  serviceDesk: number;
  sentSimulated: number;
  alreadySentSimulated: number;
  failedSimulated: number;
}

export interface DispatchReceipt {
  receiptId: string;
  runId: string;
  revisionNumber: number;
  sourceSection: string;
  taskTitle: string;
  ownerRole: string;
  channel: 'email' | 'service_desk';
  toolName: string;
  recipient?: string | null;
  destination: string;
  status: 'sent_simulated' | 'already_sent_simulated' | 'failed_simulated';
  simulated: true;
  createdAt: string;
  payloadPreview: string;
}
