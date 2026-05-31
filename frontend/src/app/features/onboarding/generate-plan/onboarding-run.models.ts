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
  errorMessage?: string;
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
