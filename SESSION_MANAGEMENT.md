# Session Management Guide

## Overview

The AMR-QTS project includes two Python scripts to manage development sessions safely:

- **`start_session.py`** — Begin a work session (pull latest, load context)
- **`end_session.py`** — End a work session (commit, push, log changes)

These scripts ensure:
- ✅ No lost work due to forgetting to commit/push
- ✅ Proper Git workflow (pull before work, push after)
- ✅ Automatic change logging for audit trail
- ✅ Quick context loading for AI assistants
- ✅ Consistent workflow across all IDEs/tools

---

## Quick Start

### Starting a Session
```bash
python start_session.py
```

### Ending a Session
```bash
python end_session.py
```

That's it! The scripts handle everything else interactively.

---

## start_session.py — Detailed Usage

### What It Does

1. **Checks Git status** — Ensures you're in a Git repository
2. **Handles uncommitted changes** — Offers to stash if you have work in progress
3. **Pulls latest code** — Syncs with remote repository
4. **Displays project context** — Shows key info from PROJECT_CONTEXT.md
5. **Shows current tasks** — Displays incomplete tasks from task.md
6. **Lists recent commits** — Shows last 3 commits for context
7. **Creates session log** — Records session start time and state

### Basic Usage

```bash
# Standard start (interactive)
python start_session.py

# Start on a specific branch
python start_session.py --branch feature/new-module

# Skip git pull (work offline)
python start_session.py --no-pull

# Quick start (minimal output)
python start_session.py --quick
```

### Command-Line Options

| Option | Short | Description |
|--------|-------|-------------|
| `--branch BRANCH` | `-b` | Checkout specified branch before starting |
| `--no-pull` | | Skip git pull (offline mode) |
| `--quick` | `-q` | Minimal output, skip context display |

### Example Output

```
======================================================================
                      AMR-QTS SESSION START
======================================================================

✓ Git repository detected
✓ Working directory is clean
ℹ Pulling latest changes from origin/main...
✓ Successfully pulled latest changes

======================================================================
                      SESSION INFORMATION
======================================================================

ℹ Session started: 2026-02-28 14:30:00
ℹ Working directory: /home/user/AMR-QTS
ℹ Python version: 3.12.2
ℹ Git branch: main
✓ Virtual environment active: /home/user/AMR-QTS/venv

======================================================================
                      PROJECT CONTEXT
======================================================================

## 🎯 What This File Is For
  A complete context file for AI assistants...

## 📊 Project Identity
  Name: AMR-QTS...

📖 Full context available in: docs/PROJECT_CONTEXT.md
💡 Share this file with AI assistants for full project understanding

======================================================================
                      CURRENT TASKS
======================================================================

## Phase 1 — Research & Backtesting
  ⧖ - [ ] Isolate backtest each module
  ⧖ - [ ] Edge validation tests

======================================================================
                      RECENT COMMITS (Last 3)
======================================================================

a1b2c3d - John Doe - 2 hours ago
  feat: implement HMM regime detector

d4e5f6g - John Doe - 1 day ago
  chore: update project structure

...

======================================================================
                      SESSION READY
======================================================================

✓ Development session started successfully!

Quick tips:
  • Run python end_session.py when done
  • Read docs/PROJECT_CONTEXT.md for AI assistants
  • Check docs/task.md for current tasks
  • Session log: logs/sessions/session_start_20260228_143000.log
```

### Working with AI Assistants

When starting a session and switching to a new AI tool:

```bash
# 1. Start session
python start_session.py

# 2. In your AI chat (Claude, Cursor, Copilot, etc.)
"Read docs/PROJECT_CONTEXT.md to understand this project"

# 3. Begin work
```

The AI will have full context of:
- Project architecture
- Current development state
- Coding standards
- Key concepts and terminology

---

## end_session.py — Detailed Usage

### What It Does

1. **Detects all changes** — Shows modified, new, and deleted files
2. **Stages changes** — Adds all changes to Git staging area
3. **Creates commit** — With your message or auto-generated one
4. **Pushes to remote** — Syncs your work to GitHub
5. **Logs changes** — Creates detailed change log in `logs/sessions/`
6. **Prompts task update** — Reminds you to update task.md

### Basic Usage

```bash
# Interactive mode (recommended)
python end_session.py

# With commit message
python end_session.py -m "feat: implement signal decay test"

# Commit but don't push
python end_session.py --no-push

# Amend previous commit
python end_session.py --amend

# Quick mode (no prompts)
python end_session.py --quick -m "fix: bug in HMM detector"
```

### Command-Line Options

| Option | Short | Description |
|--------|-------|-------------|
| `--message MSG` | `-m` | Commit message |
| `--no-push` | | Commit locally but skip push |
| `--amend` | | Amend previous commit |
| `--quick` | `-q` | Skip prompts (requires -m) |
| `--no-log` | | Skip change log creation |

### Commit Message Conventions

The script suggests using conventional commits:

| Prefix | Usage |
|--------|-------|
| `feat:` | New feature (e.g., "feat: add HMM regime detector") |
| `fix:` | Bug fix (e.g., "fix: correct ATR calculation") |
| `docs:` | Documentation (e.g., "docs: update README") |
| `refactor:` | Code refactoring (e.g., "refactor: simplify backtest engine") |
| `test:` | Adding tests (e.g., "test: add edge validation tests") |
| `chore:` | Maintenance (e.g., "chore: update dependencies") |

### Example Output

```
======================================================================
                      AMR-QTS SESSION END
======================================================================

======================================================================
                      CHANGES DETECTED
======================================================================

Modified files (3):
  M src/regime/hmm_detector.py
  M src/strategies/module1_trend.py
  M config/settings.py

New files (2):
  A tests/test_hmm_detector.py
  A reports/backtest_results/module1_isolated.csv

Total: 5 file(s) changed

⚠ Proceed with commit and push? (y/n): y

ℹ Staging all changes...
✓ All changes staged successfully

======================================================================
                      COMMIT MESSAGE
======================================================================

ℹ Suggested commit message types:
  feat:     New feature
  fix:      Bug fix
  docs:     Documentation
  refactor: Code refactoring
  test:     Adding tests
  chore:    Maintenance

Default: chore: update 3 file(s), add 2 file(s) - session end 2026-02-28 16:45

Enter commit message (or press Enter for default): feat: complete Module 1 isolated backtest

ℹ Committing changes...
✓ Committed with message: feat: complete Module 1 isolated backtest

✓ Change log created: logs/sessions/session_end_20260228_164530.log

ℹ Pushing to origin/main...
✓ Successfully pushed to origin/main

======================================================================
                      TASK UPDATE
======================================================================

ℹ Did you complete any tasks during this session?
Task file: docs/task.md

Open task.md to update? (y/n): y

======================================================================
                      SESSION SUMMARY
======================================================================

ℹ Session ended: 2026-02-28 16:45:30
ℹ Branch: main
ℹ Change log: logs/sessions/session_end_20260228_164530.log
✓ Latest commit: a1b2c3d

======================================================================
                      SESSION COMPLETED
======================================================================

✓ Development session ended successfully!

Next steps:
  • Changes are saved and pushed to Git
  • Run python start_session.py for next session
  • Check logs/sessions/ for session logs
```

### Change Log Format

Each session end creates a detailed log file in `logs/sessions/`:

```
Session End: 2026-02-28 16:45:30
======================================================================

Branch: main
Commit: a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0
Message: feat: complete Module 1 isolated backtest

Changes Summary:
  Modified: 3 file(s)
  New:      2 file(s)
  Deleted:  0 file(s)
  Total:    5 file(s)

Modified Files:
  - src/regime/hmm_detector.py
  - src/strategies/module1_trend.py
  - config/settings.py

New Files:
  + tests/test_hmm_detector.py
  + reports/backtest_results/module1_isolated.csv

======================================================================
Detailed Diff Stats:

 config/settings.py                              |  15 +++-
 reports/backtest_results/module1_isolated.csv   | 245 +++++++++++++++++++
 src/regime/hmm_detector.py                      |  82 +++---
 src/strategies/module1_trend.py                 |  34 +--
 tests/test_hmm_detector.py                      | 156 ++++++++++++
 5 files changed, 478 insertions(+), 54 deletions(-)
```

---

## Typical Workflow

### Morning Session Start

```bash
# Terminal
cd ~/AMR-QTS
python start_session.py

# Read context if needed
cat docs/PROJECT_CONTEXT.md

# Activate virtual environment if not auto-activated
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Start your IDE/AI tool
code .  # VS Code
# or open in Cursor, etc.
```

### During Work

- Make changes to code
- Test changes
- Run experiments
- Don't worry about Git — handle it at session end

### Evening Session End

```bash
# Terminal
python end_session.py

# Follow prompts:
# 1. Review changes
# 2. Enter commit message
# 3. Confirm push
# 4. Update task.md if needed

# Done!
```

---

## Advanced Scenarios

### Scenario 1: Quick Fix on Different Branch

```bash
# Start
python start_session.py --branch hotfix/urgent-bug --quick

# Make fix
# ... edit files ...

# End
python end_session.py -m "fix: resolve critical HMM convergence issue" --quick
```

### Scenario 2: Offline Work

```bash
# Start without pulling
python start_session.py --no-pull

# Work offline
# ... make changes ...

# End without pushing (commit locally)
python end_session.py --no-push

# Later, when online
git push origin main
```

### Scenario 3: Experimental Feature

```bash
# Create and switch to feature branch
python start_session.py --branch feature/experiment

# Work on feature
# ... make changes ...

# Commit but review before pushing
python end_session.py --no-push

# Review commit
git log -1 -p

# Push when satisfied
git push origin feature/experiment
```

### Scenario 4: Amend Last Commit

```bash
# Realize you forgot something after session end
# ... make additional changes ...

# Amend the previous commit
python end_session.py --amend
```

### Scenario 5: Multi-Tool Development

```bash
# Morning: VS Code work
python start_session.py
code .
# ... work in VS Code ...
python end_session.py -m "feat: implement data preprocessing"

# Afternoon: Jupyter notebook analysis
python start_session.py --quick
jupyter notebook
# ... run experiments ...
python end_session.py -m "docs: add exploratory analysis notebook"

# Evening: Cursor AI pair programming
python start_session.py --quick
cursor .
# ... AI-assisted coding ...
python end_session.py -m "refactor: optimize backtest engine performance"
```

---

## Troubleshooting

### "Not a Git repository"

**Problem:** Running scripts outside the project directory

**Solution:**
```bash
cd /path/to/AMR-QTS
python start_session.py
```

### "Pull failed"

**Problem:** Merge conflicts with remote

**Solution:**
```bash
# Stash your changes
git stash

# Pull
git pull origin main

# Apply stash and resolve conflicts
git stash pop

# Or skip pull and work offline
python start_session.py --no-pull
```

### "Push failed"

**Problem:** Remote has changes you don't have locally

**Solution:**
```bash
# Pull and merge
git pull origin main --rebase

# Then push
git push origin main
```

### "Changes not detected"

**Problem:** Files in `.gitignore` won't show up

**Solution:** This is intentional! Data files, models, and cache files should not be committed. Only commit code, configs, and documentation.

### "Virtual environment not active"

**Problem:** Script warns venv is not activated

**Solution:**
```bash
# Linux/Mac
source venv/bin/activate

# Windows
venv\Scripts\activate

# Then run script
python start_session.py
```

---

## Best Practices

### DO ✅

- **Start every session** with `start_session.py`
- **End every session** with `end_session.py`
- **Write meaningful commit messages** using conventional commit prefixes
- **Update task.md** when completing tasks
- **Review changes** before confirming commit
- **Use feature branches** for experimental work
- **Keep sessions focused** on one task/feature

### DON'T ❌

- **Don't commit data files** (they're in `.gitignore` for a reason)
- **Don't force push** without understanding implications
- **Don't skip the scripts** and use raw git commands (scripts provide safety)
- **Don't work across multiple branches** without ending session first
- **Don't forget to push** (unless intentionally working offline)

---

## Integration with AI Tools

### Claude (Web/Desktop)

```bash
# Start session
python start_session.py

# In Claude chat
"Read the PROJECT_CONTEXT.md file to understand this project, then help me with [task]"

# Work with Claude
# ... get code suggestions, debug, etc. ...

# End session
python end_session.py -m "feat: [what you built with Claude]"
```

### Cursor IDE

```bash
# Start session
python start_session.py

# Open in Cursor
cursor .

# In Cursor AI chat (Cmd/Ctrl + K or Cmd/Ctrl + L)
@PROJECT_CONTEXT.md

# Work in Cursor with AI assistance
# ... code with AI ...

# End session
python end_session.py -m "feat: [what you built]"
```

### GitHub Copilot (VS Code)

```bash
# Start session
python start_session.py

# Open in VS Code
code .

# Copilot will read your code context
# Work normally with Copilot suggestions

# End session
python end_session.py -m "feat: [what you built]"
```

### Jupyter Notebook

```bash
# Start session
python start_session.py --quick

# Launch Jupyter
jupyter notebook

# Work in notebooks
# Save notebooks frequently

# End session
python end_session.py -m "docs: add [notebook name] analysis"
```

---

## Session Log Management

### Location
All session logs are stored in:
```
logs/sessions/
├── session_start_20260228_090000.log
├── session_end_20260228_120000.log
├── session_start_20260228_140000.log
└── session_end_20260228_170000.log
```

### Cleanup

Logs can accumulate over time. Clean up old logs periodically:

```bash
# Keep last 30 days, delete older
find logs/sessions/ -name "*.log" -mtime +30 -delete

# Or manually review and delete
ls -lt logs/sessions/
rm logs/sessions/session_*_old_date.log
```

### Git Tracking

Session logs are typically in `.gitignore` (local audit trail only). If you want to track them:

```bash
# Remove from .gitignore
# Then commit
git add logs/sessions/
git commit -m "docs: add session logs for project tracking"
```

---

## FAQ

**Q: Do I need to run these scripts every time?**  
A: Yes! They ensure you never lose work and maintain a clean Git history.

**Q: Can I use regular git commands instead?**  
A: Yes, but the scripts provide safety checks and automation. If you're comfortable with Git, you can use either.

**Q: What if I forget to run end_session.py?**  
A: Your changes are still on your machine. Run it when you remember, and it will commit everything since the last commit.

**Q: Can I modify the scripts?**  
A: Absolutely! They're Python scripts in your project. Customize to your workflow.

**Q: Do the scripts work on Windows?**  
A: Yes! They use cross-platform Python and Git commands.

**Q: What if I have merge conflicts?**  
A: The scripts will detect conflicts and prompt you to resolve them manually before proceeding.

---

## Summary

| Script | Purpose | Key Benefit |
|--------|---------|-------------|
| `start_session.py` | Begin work session | Ensures you have latest code + context |
| `end_session.py` | End work session | Never forget to commit/push + automatic logging |

**Golden Rule:** Always bookend your work sessions with these scripts!

---

*Last Updated: 2026-02-28*
