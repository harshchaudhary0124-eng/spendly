---
description: Runs parallel security and quality code 
  review for a specific Spendly feature. Pass the spec 
  name as argument e.g. /code-review-feature 03-login
allowed-tools: Bash(git diff), Bash(git diff --staged)
---

Run the full code review pipeline for the feature 
specified in $ARGUMENTS.

If no argument is provided, stop immediately and say:
"Please provide a spec name. Usage: /code-review-feature 
<spec-name> e.g. /code-review-feature 03-login"

## Pre-flight Check

Before invoking any subagents:

1. Verify the spec file exists at `.claude/specs/$ARGUMENTS.md`. 
   If it does not exist, stop immediately and say:
   "Spec file not found at .claude/specs/$ARGUMENTS.md. 
   Please check the spec name and try again."

2. Collect the diff:
   - Run `git diff` for unstaged changes
   - Run `git diff --staged` for staged changes
   - Combine both into a single diff

   If both are empty, stop immediately and say:
   "No changes detected. Implement the feature before 
   running code review."

---

## Step 1: Parallel Review

Invoke both subagents simultaneously with the same 
context:

**spendly-security-reviewer** receives:
- The combined diff from the pre-flight check
- Spec file for context: `.claude/specs/$ARGUMENTS.md`
- Source files to reference: `app.py`, 
  `database/` directory, and `templates/` directory
- Instruction: Review only the changed code for 
  security vulnerabilities. Do not comment on quality 
  or style. Treat stub routes as out of scope.

**spendly-quality-reviewer** receives:
- The combined diff from the pre-flight check
- Spec file for context: `.claude/specs/$ARGUMENTS.md`
- Source files to reference: `app.py`, `database/` 
  directory, and `templates/` directory
- Instruction: Review only the changed code for quality, 
  Flask best practices, and maintainability. Do not 
  comment on security concerns.

Both subagents must run in parallel. Do not wait for 
one to finish before starting the other.

---

## Step 2: Unified Report

Once both subagents have completed, combine their 
findings into a single unified report. De-duplicate 
any overlapping findings — if both agents flagged the 
same line for different reasons, merge them into one 
finding with both perspectives noted.

Structure the combined report as:
Code Review Report — $ARGUMENTS
Security Findings
[spendly-security-reviewer output]
Quality Findings
[spendly-quality-reviewer output]
Combined Action Plan
Ordered checklist of everything that needs to be fixed,
prioritized by severity:

1. Security 💡 Things to learn from (critical findings first)
2. Quality 💡 Worth improving items
3. Security 🌱 Nice to have items
4. Quality 🌱 Polish ideas items

Overall Verdict
APPROVED — no 💡 findings from either reviewer
APPROVED WITH SUGGESTIONS — only 🌱 findings; 
  safe to commit, address in a future step
CHANGES REQUESTED — one or more 💡 findings present;
  address the action plan before committing
---

## Step 3: Ask for Approval

After presenting the unified report, ask:

"Do you want me to implement the action plan now?"

Wait for explicit user confirmation before making 
any changes. Do not touch any files until the user 
approves.

---

## Rules
- Do NOT edit any files before user approval
- Do NOT start one reviewer before the other — 
  both must run in parallel
- Do NOT skip the pre-flight checks (spec file and diff)
- If either subagent fails or returns no output, 
  report it and do not present a partial review 
  as complete