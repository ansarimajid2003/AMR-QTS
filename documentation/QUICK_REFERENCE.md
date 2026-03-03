# Session Management — Quick Reference Card

## 🚀 Start Session

```bash
python start_session.py
```

**Options:**
- `--branch feature/name` — Switch to branch
- `--no-pull` — Skip git pull (offline)
- `--quick` — Minimal output

## 🏁 End Session

```bash
python end_session.py
```

**Options:**
- `-m "feat: message"` — Commit message
- `--no-push` — Commit but don't push
- `--amend` — Amend last commit
- `--quick` — Skip prompts

## 📝 Commit Message Prefixes

| Prefix | Usage |
|--------|-------|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `docs:` | Documentation |
| `refactor:` | Code refactoring |
| `test:` | Adding tests |
| `chore:` | Maintenance |

## 🎯 Typical Workflow

```bash
# Morning
python start_session.py
source venv/bin/activate
code .

# [... work ...]

# Evening
python end_session.py
```

## 🔧 Common Commands

```bash
# Quick fix on branch
python start_session.py -b hotfix/bug --quick
# ... fix ...
python end_session.py -m "fix: resolve bug" --quick

# Offline work
python start_session.py --no-pull
# ... work ...
python end_session.py --no-push

# Amend last commit
python end_session.py --amend
```

## 🤖 AI Tool Integration

```bash
# Start session
python start_session.py

# In AI chat:
"Read PROJECT_CONTEXT.md to understand this project"

# Work with AI
# ...

# End session
python end_session.py -m "feat: [what you built]"
```

## 📍 Key Files

- `PROJECT_CONTEXT.md` — Full project context for AI
- `task.md` — Current task list
- `logs/sessions/` — Session logs
- `.gitignore` — Excluded files (data, models)

## ⚠️ Remember

- ✅ Always start with `start_session.py`
- ✅ Always end with `end_session.py`
- ✅ Write meaningful commit messages
- ✅ Update task.md when completing tasks
- ❌ Don't commit data files
- ❌ Don't force push without reason

## 📞 Help

```bash
python start_session.py --help
python end_session.py --help
```

Full guide: `SESSION_MANAGEMENT.md`

---

*Print this for your desk! 📋*
