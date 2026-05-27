# Contributor Onboarding Guide

## Welcome Contributors

This guide helps new contributors and GSSOC participants get started with SecuScan.

---

# Repository Areas

| Area | Description |
|---|---|
| frontend/ | React frontend |
| backend/ | FastAPI backend |
| plugins/ | Plugin integrations |
| docs/ | Documentation |

---

# Recommended Beginner Contributions

Good beginner areas:

- Documentation improvements
- UI polish
- Validation fixes
- Test coverage
- Plugin metadata cleanup

---

# Development Workflow

1. Fork repository
2. Clone locally
3. Create branch
4. Make changes
5. Commit changes
6. Push branch
7. Open pull request

---

# Branch Naming

Examples:

```text
docs/update-api-guide
fix/plugin-validation
feat/frontend-empty-state
```

---

# Pull Request Tips

- Keep PRs focused
- Add clear descriptions
- Link related issues
- Avoid unrelated changes

---

# Testing Expectations

Backend:

```bash
./testing/test_python.sh
```

Frontend:

```bash
cd frontend
npm run test
```

---

# Common Mistakes

- Editing unrelated files
- Large PRs
- Missing issue references
- Skipping documentation updates

---

# Troubleshooting

## Permission Denied

```bash
chmod +x setup.sh start.sh
```

## Python Version Issues

Use Python 3.11 or newer.