# AAMAD Flow For Codex

Use this file as the project-local handoff guide from generic AAMAD bootstrap into AAMAD Flow.

## Prime Directive

The human is the Agentic Architect. Treat them as the final reviewer for every artifact and the owner of technical, experience, business, and role-definition tradeoffs.

## Bootstrap Boundary

AAMAD Bootstrap only adapts AAMAD methodology artifacts for Codex. It must not start product discovery, define an MVP, choose the application architecture, bootstrap application code, or refine project-specific agent roles.

Those activities begin only after the Agentic Architect explicitly starts AAMAD Flow.

## Review Gate

After generating or updating any artifact, stop and request review from the human Agentic Architect before advancing.

Do not continue to the next persona, phase, implementation stage, or generated artifact until the human explicitly approves, requests changes, or redirects the workflow.

## Starting AAMAD Flow

When the user asks to start or continue AAMAD Flow:

1. Inspect `.codex/aamad/state.md`, this file, `.codex/aamad/review-log.md`, and `AGENTS.md`.
2. Confirm that the bootstrap review gate has been approved or explicitly redirected.
3. Collaborate with the Agentic Architect to decide the next artifact, persona, or role-refinement step.
4. Produce only the approved artifact or change.
5. Stop for Agentic Architect review.

## Role Refinement

Treat copied AAMAD agent definitions as generic seeds. Refine or create technical agent roles only inside AAMAD Flow, with Agentic Architect approval, and prefer a generic agent-role creation/refinement skill when available.

## Persona Invocation In Codex

Cursor-style `@agent` invocation is not native here. To invoke a persona, explicitly say: "Assume the AAMAD <persona> persona using `.codex/aamad/agents/...` and produce <artifact>."
