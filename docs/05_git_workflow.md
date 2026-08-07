# Git Branching Strategy & Workflow

To maintain production stability and seamless feature development, ABS ERP enforces a Git Flow branching strategy.

---

## 🌲 Branch Structure

```text
main (Production)
 │
 ├── develop (Staging & Integration)
 │    │
 │    ├── feature/api
 │    ├── feature/inventory
 │    ├── feature/procurement
 │    ├── feature/hr
 │    ├── feature/mobile
 │    └── hotfix/*
```

---

## 📌 Branch Roles

1. **`main`**:
   - Production-ready stable branch. Every commit on `main` represents a tested release tagged with a semantic version.

2. **`develop`**:
   - Integration branch for completed features. Automated unit tests run on every pull request into `develop`.

3. **`feature/*`**:
   - Dedicated short-lived feature branches created off `develop` (e.g. `feature/inventory`, `feature/hr`, `feature/mobile`).

4. **`hotfix/*`**:
   - Urgent production hotfixes created directly off `main` and merged back into both `main` and `develop`.

---

## ✍️ Commit Conventions

Use Conventional Commit prefixes:
- `feat:` New feature implementation
- `fix:` Bug fix
- `docs:` Documentation update
- `refactor:` Code restructuring without behavior changes
- `test:` Unit or integration tests addition
