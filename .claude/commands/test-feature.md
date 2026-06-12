---
description: Writes and runs tests for a specific Spendly feature. Pass the spec name as argument e.g. /test-feature 05-backend-connection
allowed-tools: Bash(python -m pytest)
---

Run the full testing pipeline for the feature specified 
in $ARGUMENTS.

If no argument is provided, stop immediately and say:
"Please provide a spec name. Usage: /test-feature 
<spec-name> e.g. /test-feature 05-backend-connection"

If `.claude/specs/$ARGUMENTS.md` does not exist, stop 
immediately and say:
"Spec file not found at .claude/specs/$ARGUMENTS.md. 
Please check the spec name and try again."

---

## Step 1: Write Tests

Invoke the **spendly-test-writer** subagent with the 
following context:

- Spec file to base tests on: 
  `.claude/specs/$ARGUMENTS.md`
- Source files for architecture context only (do NOT
  derive test logic from these):
  - `app.py`
  - `database/` directory
  - `templates/` directory
- Existing test infrastructure to follow conventions from:
  - `tests/` directory
  - `conftest.py` (if present)
- Output test file to create:
  `tests/test_$ARGUMENTS.py`
- Instruction: Write tests based on what the spec says
  the feature SHOULD do. Do NOT mirror implementation
  logic. Cover all applicable categories: happy path,
  validation, boundary conditions, authentication,
  authorization, security (SQL injection, XSS, form
  tampering), error handling, DB side effects, and
  regression protection. If the spec is ambiguous on
  any behavior, stop and ask before writing those tests.

Wait for spendly-test-writer to fully complete and 
confirm the test file has been written before 
proceeding to Step 2.

---

## Step 2: Run Tests

Once spendly-test-writer has finished, invoke the 
**spendly-test-runner** subagent with the following 
context:

- Test file to execute:
  `tests/test_$ARGUMENTS.py`
- Spec file for context:
  `.claude/specs/$ARGUMENTS.md`
- Source files to analyze against when diagnosing 
  failures:
  - `app.py`
  - `database/` directory
- Run command:
  `python -m pytest tests/test_$ARGUMENTS.py -v`
- Instruction: Run ONLY the specified test file. Do
  NOT run the full test suite. Perform root-cause
  analysis on every failure and classify it using
  the full five-category framework — Implementation
  Bug, Incorrect Test, Missing Feature, Environment
  Failure, or Regression. Flag regressions prominently.
  Provide specific, architecture-compliant fix guidance
  for each failure.

---

## Handoff Rules

- Do NOT start Step 2 until Step 1 is fully complete
- Do NOT attempt to fix any code regardless of what 
  the test results show
- Do NOT run any tests beyond `tests/test_$ARGUMENTS.py`
- If spendly-test-writer reports it could not write 
  the test file, stop and report the reason — do NOT 
  proceed to Step 2

---

## Final Output

After both subagents complete, produce a combined 
summary:

### Testing Pipeline Report — $ARGUMENTS

**Step 1 — Tests Written**
- List each test written with a one-line description 
  of which spec requirement it validates

**Step 2 — Test Results**
- Mirror the spendly-test-runner's structured report

**Verdict**
One of:
- ✅ Ready for code review — all tests pass
- ❌ Needs fixes — list the failing tests and their root causes