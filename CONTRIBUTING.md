# Contributing to Mommy Bank 🐷

Thank you for helping build the family bank! This project has one unusual rule,
so let's get it out of the way first.

## The house rule: AI writes the code, humans direct and review

**All code in this repository is written by AI coding agents. Humans do not
write code here.** Humans are absolutely welcome — as product owners, issue
reporters, reviewers, testers, and merge approvers. This is a deliberate
experiment in human-directed, AI-implemented development:

| Role | Who | Does what |
|---|---|---|
| Director | 🧑 Human | Opens issues describing *what* and *why* (bug reports, feature requests, UX feedback, screenshots) |
| Implementer | 🤖 AI agent | Reads [`AGENTS.md`](AGENTS.md), writes the code + tests, keeps the three surfaces (GUI / CLI / MCP) in parity |
| Reviewer | 🧑 Human | Reviews the PR, requests changes (as new issues/comments), approves |
| Merger | 🧑 Human | Merges when CI is green and review is approved |

If you want to contribute code: open an issue first, then have your AI agent of
choice (Claude Code, ZCode, Cursor, Copilot Workspace, …) implement it in a fork
following [`AGENTS.md`](AGENTS.md). The PR description should say which agent
produced it and link the issue it implements. Hand-written patches will be
politely closed with a pointer to this file — nothing personal, it's the
project's policy. 💕

## Standard PR process

1. **Issue first.** Every PR references an open issue (bug or proposal).
2. **Fork & branch.** Branch from `main` as `feat/<issue#>-short-description`,
   `fix/<issue#>-…`, or `docs/<issue#>-…`.
3. **Implement with an AI agent** guided by [`AGENTS.md`](AGENTS.md):
   - service logic + unit tests → router + API tests → CLI + MCP parity → frontend.
   - Keep the invariants in AGENTS.md (integer cents/seconds, append-only
     ledger, lazy interest accrual, kids read-only, parameter-bound SQL, no
     credential literals).
4. **Tests must pass.** CI runs both suites and they are the merge gate:
   ```bash
   cd backend  && .venv/bin/python -m pytest    # or .venv/Scripts/python on Windows
   cd frontend && npm test && npm run build
   ```
   New behavior needs new tests; GUI changes need a browser sanity pass
   (desktop + 390×844 mobile).
5. **Small PRs, conventional commits** (`feat:`, `fix:`, `docs:`, `test:`,
   `chore:`). One logical change per PR.
6. **Human review & approve**, then a human merges. Agents may push branches
   and open PRs; agents never merge to `main`.

## Non-code contributions (fully human, always welcome ❤️)

- **Bug reports** with steps/screenshots — the fuel for every agent fix.
- **Ideas**: age-mode improvements, new exchange-rule presets, funnier pig moods.
- **UX feedback** from real kids and real parents — tell us which screen confused them.
- **Docs & translations** — flagged the same way; an agent applies the edit, you review.
- **QA**: run the 13-point browser pass in [`qa/QA_REPORT.md`](qa/QA_REPORT.md)
  on your own family install and report results.

## Ground rules

- Be kind; this is a family project, possibly literally about someone's family.
- No credential literals, ever — secrets come from env vars.
- Keep the repo runnable: `docker compose up --build -d` must always work.
- Security reports: open a private security advisory on GitHub, not a public issue.
