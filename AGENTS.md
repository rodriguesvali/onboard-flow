# AAMAD Agent Framework

This project uses the AAMAD framework for multi-agent development.
See the full agent definitions adapted for Codex under `.codex/aamad/agents/`.

## Agent Personas
- **@product-mgr** — Product Manager: Orchestrates product vision and requirements
- **@system.arch** — System Architect: Produces SAD and SFS documents
- **@project.mgr** — Project Manager: Scaffolds project and environment
- **@frontend.eng** — Frontend Engineer: Builds the Angular + PrimeNG MVP workbench
- **@backend.eng** — Backend Engineer: Builds the Python CrewAI backend service
- **@integration.eng** — Integration Engineer: Connects the Angular workbench to the Python CrewAI API
- **@qa.eng** — QA Engineer: Validates MVP functionality
- **@devops.eng** — DevOps Engineer: Prepares reproducibility, CI/CD, deployment readiness, observability, and safe operations

## Workflow
1. **Define** (Phase 1): @product-mgr → Market Research → PRD → @system.arch → SAD
2. **Build** (Phase 2): @project.mgr → @frontend.eng / @backend.eng → @integration.eng → @qa.eng
3. **Deliver** (Phase 3): DevOps deployment

## Rules
All development follows AAMAD core rules. See project-context/ for artifacts.

## Agent Definitions
See `.codex/aamad/agents/` for AAMAD persona definitions adapted for Codex.

<!-- AAMAD-CODEX:START -->
# AAMAD Bootstrap For Codex

This repository has been prepared for AAMAD work in Codex.

## Human Role

The human is the Agentic Architect. The Agentic Architect reviews every generated or updated artifact before any next stage begins.

## AAMAD Flow

Use the global `$aamad-flow` skill and `.codex/aamad/workflow.md` as its handoff guide after bootstrap. When asked to start or continue AAMAD Flow, inspect `.codex/aamad/state.md`, then collaborate with the Agentic Architect on the next approved artifact or role-refinement step.

## Bootstrap Boundary

AAMAD Bootstrap only adapts AAMAD methodology artifacts for Codex. Project discovery, MVP definition, system architecture, implementation planning, application bootstrap, and project-specific agent-role refinement happen later through AAMAD Flow.

## Agent Role Seeds

AAMAD-generated agent descriptions under `.codex/aamad/agents/` are generic seeds. They are not final project-specific technical roles until AAMAD Flow refines them with the Agentic Architect.

## Mandatory Review Gate

After generating or updating any artifact, stop and ask the Agentic Architect for review. Do not move to the next stage until the Architect explicitly approves, requests changes, or redirects the workflow.

## Current Repository Profile

- State: empty
- Languages: not detected
- Frameworks: not detected
- Package managers: not detected

## AAMAD Codex Files

- `.codex/aamad/state.md`
- `.codex/aamad/workflow.md`
- `.codex/aamad/review-log.md`
- `.codex/aamad/mcp-rules.md`
- `.codex/aamad/templates/`
<!-- AAMAD-CODEX:END -->
