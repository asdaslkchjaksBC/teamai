---
name: smart-commit
description: Analyze Git working tree changes, split them into logical commits, draft project-aligned commit messages, ask for user confirmation, then commit in order. Use when a user asks to commit current changes, organize messy diffs into clean commits, or improve commit message quality before committing.
---

# Smart Commit

Analyze current Git changes, propose a logical commit plan, confirm with the user, then execute commits safely.

## Workflow

### 1. Collect Context

Run these commands first:

- `git status`
- `git diff`
- `git diff --cached`
- `git log --oneline -15`

If there are no changes (staged and unstaged), stop and tell the user.

### 2. Group Changes into Commit Units

Classify all changed files by intent and dependency:

- Keep one commit for one coherent purpose.
- Keep related multi-file changes in the same commit.
- Split unrelated changes into separate commits.
- Avoid mixing refactor and behavior change unless tightly coupled.

### 3. Draft Commit Messages

Use format: `[TYPE]Short purpose`

Default type mapping:

- `[新增]`: New feature, new file, new capability
- `[修复]`: Bug fix or correctness fix
- `[修改]`: Behavior adjustment or logic update
- `[优化]`: Performance/readability/resource optimization
- `[重构]`: Structural refactor without intended behavior change
- `[更新]`: Dependency or resource update
- `[版本]`: Version bump only

Write concise Chinese purpose statements focused on intent, not low-level details.

### 4. Present Plan Before Committing

Show the user:

- Proposed commit count and order
- File list for each commit
- Brief summary for each commit
- Draft commit message for each commit

Always ask for confirmation or edits before running commit commands.

### 5. Execute Commits After Confirmation

For each confirmed commit, run in order:

- `git add <explicit-file-paths>`
- `git commit -m "<message>"`

After all commits, show a compact result summary (hash + message per commit).

## Safety Rules

- Never use `git add -A` or `git add .`
- Never commit without user confirmation
- Never use heredoc for commit message input
- Never add `Co-Authored-By` unless explicitly requested
- Do not stage sensitive files (for example: `.env`, `*.pem`, `*credentials*`, secrets files)

## Handling Edge Cases

- If only staged changes exist, still review and present a plan before committing.
- If both staged and unstaged changes exist, include both in analysis and make staging explicit per commit.
- If user requests a specific message style, keep this workflow but adapt message wording.
