# Subagent Policy

This policy applies to the whole Swaflow project.

Use subagents whenever the work has independent slices that can be analyzed or built in parallel.
Spawn as many subagents as needed for the task, as long as each one has a narrow scope and materially improves the result.

## Scope

- Applies to all project work: architecture, implementation, review, investigation, documentation, and planning.
- Use it for any part of the repo, not just backend or architecture tasks.
- Prefer parallel subagents when the task has distinct axes that do not block each other.

## When To Spawn

- Architecture decisions that span several domains.
- Security, payments, multi-tenant, or webhook analysis that benefits from separate lenses.
- Code review or investigation that needs distinct viewpoints.
- Large research or documentation tasks that can be split cleanly.
- Any project task where additional independent perspectives will improve correctness, safety, or completeness.

## What To Pass

- One bounded task per subagent.
- The goal and the expected deliverable.
- Only the context needed to work independently.
- Constraints that must not be violated.
- The output shape you want back.

## What To Require

- A concise recommendation or finding.
- Relevant risks or open questions.
- Evidence or file references when available.
- No duplicated work between subagents.
- One clear output per subagent, with no wandering outside scope.

## How To Merge

- Deduplicate overlapping points.
- Group results into agreements, conflicts, and unknowns.
- Resolve conflicts by priority: constraints first, then risk, then cost, then elegance.
- Keep the parent responsible for the final decision and any edits.

## Reusable Prompt Template

```text
You are a subagent working on Swaflow.

Task:
{task}

Scope:
{scope}

Constraints:
{constraints}

Context:
{context}

Expected output:
{output_format}

Rules:
- Stay within scope.
- Do not use tools unless explicitly allowed.
- Return only the requested output.
```

## BMad Party Mode Template

Use this when you want multiple perspectives on the same architecture or product question.

```text
You are one voice in a multi-agent discussion about Swaflow.

Task:
{question}

Your role:
{role_scope}

Shared context:
{context}

Constraints:
{constraints}

Instructions:
- Give your own view only.
- Do not summarize other agents.
- Be concrete about tradeoffs and risks.
- Keep your response short and independently useful.
```

## bmad-party-mode Usage

Use `bmad-party-mode` when the task benefits from 2-4 independent perspectives or adversarial coverage. Typical cases: backend architecture, data model, security, API contracts, integrations, UX tradeoffs, and implementation planning.

Rules:
- Split the problem into narrow slices before spawning subagents.
- Give each subagent one bounded question, one scope, and one success criterion.
- Pass only shared context that is stable and necessary.
- Keep subagents isolated; do not let them depend on each other’s outputs.
- Merge results in the parent agent and resolve conflicts by priority: constraints first, then risk, then implementation cost, then elegance.
- Use this mode only when the extra parallelism is likely to change the decision quality.

## Code Review Template

Use this when the goal is to review a diff, implementation, or design decision.

```text
You are a review subagent for Swaflow.

Scope:
{scope}

Context:
{context}

What to inspect:
{review_focus}

Output format:
1. Findings
2. Risks
3. Missing tests or evidence
4. Recommended action

Rules:
- Do not rewrite the whole solution.
- Focus on defects, regressions, and missed edge cases.
- Keep findings specific and actionable.
```

## Code Review Usage

Use subagents for code review when the change has multiple independent risk areas or needs adversarial coverage.

Rules:
- Spawn separate reviewers for correctness, edge cases, security, performance, and test coverage when relevant.
- Give each reviewer the diff, target behavior, and review focus only.
- Ask for findings, severity, and file/line references.
- Do not ask for rewrite suggestions unless a bug or design flaw is confirmed.
- Merge findings in the parent agent, dedupe overlaps, and prioritize blocking issues first.
- If no findings are returned, still check for missing tests and latent regressions before approving.
