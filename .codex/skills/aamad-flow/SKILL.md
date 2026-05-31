---
name: aamad-flow
description: Continue AAMAD Flow for the current repository after AAMAD Bootstrap. Use when the user asks to start, continue, or resume AAMAD Flow; refine project-specific agent roles; run Agentic Architect review gates; or produce approved Define, Build, or Deliver artifacts using the repository-local .codex/aamad guidance.
---

# AAMAD Flow

Use this global skill only after AAMAD Bootstrap has generated `.codex/aamad/` in the current repository.

## Start

When invoked:

1. Read `.codex/aamad/state.md`.
2. Read `.codex/aamad/workflow.md`.
3. Read `.codex/aamad/review-log.md`.
4. Read `AGENTS.md`.
5. Determine the current development-flow moment: bootstrap review, project discovery, role refinement, Define, Build, Deliver, implementation, QA, deployment, or blocked/pending validation.
6. Confirm the current review gate before producing any new artifact.
7. Support the Agentic Architect by naming the current stage, the pending decision, and the smallest valid next step.

## Operating Boundary

AAMAD Flow owns project discovery, MVP definition, architecture decisions, implementation sequencing, and project-specific agent-role refinement. AAMAD Bootstrap owns only generic methodology adaptation.

## Review Gate

After generating or updating any artifact, stop and request review from the human Agentic Architect. Do not continue to the next persona, phase, implementation stage, or generated artifact until the Agentic Architect explicitly approves, requests changes, or redirects the workflow.

Record decisions in `.codex/aamad/review-log.md`.

Project-context rule: whenever an artifact under `project-context/` is generated or changed, immediately request Agentic Architect validation and record the decision before producing another project-context artifact or implementation change.

## Delegation

Delegate work to the responsible AAMAD agent persona by reading the matching file under `.codex/aamad/agents/` before producing the artifact or implementation plan.

Default responsibility map:

- Product Manager: MRD, PRD, product scope, user and business requirements.
- System Architect: SAD, architecture plan, technical constraints, cross-system design.
- Frontend Engineer: frontend plan and UI implementation.
- Backend Engineer: backend plan, APIs, services, workers, data contracts.
- Integration Engineer: integration plan and cross-component wiring.
- QA Engineer: QA plan, test strategy, validation evidence.
- DevOps Engineer: deployment, monitoring, operations, runbooks. If no `devops-eng` agent file exists, ask the Agentic Architect whether to create/refine one before delegating DevOps work.

Only delegate the task approved for the current step. If the responsible agent role is missing, generic, or mismatched to the project scope, pause for Agentic Architect role refinement before continuing.

## Role Refinement

Treat `.codex/aamad/agents/` as generic seeds. Refine or create project-specific technical agents with the Agentic Architect before relying on them as final project roles.
