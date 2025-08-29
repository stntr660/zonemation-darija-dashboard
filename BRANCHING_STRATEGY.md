# 🌳 Git Branching Strategy

## Branch Overview

### `main` (Protected)
- **Purpose**: Stable, tested code ready for production
- **Deploy to**: Staging environment
- **Merges from**: `develop` via Pull Request
- **Protected**: Yes - requires PR review

### `production` (Protected)
- **Purpose**: Production-ready code with all security configurations
- **Deploy to**: Production environment
- **Merges from**: `main` after staging validation
- **Contains**: Production configs, security hardening, deployment files
- **Protected**: Yes - requires PR review + approval

### `develop`
- **Purpose**: Integration branch for features
- **Deploy to**: Development environment
- **Merges from**: Feature branches
- **Contains**: Latest development code

### Feature Branches
- **Naming**: `feature/description` (e.g., `feature/add-whisper-model`)
- **Created from**: `develop`
- **Merged to**: `develop` via Pull Request

### Hotfix Branches
- **Naming**: `hotfix/description` (e.g., `hotfix/security-patch`)
- **Created from**: `production`
- **Merged to**: `production` and `main`

## Workflow

### 1. Feature Development
```bash
# Create feature branch from develop
git checkout develop
git pull origin develop
git checkout -b feature/new-feature

# Work on feature
# ... make changes ...
git add .
git commit -m "Add new feature"

# Push and create PR
git push origin feature/new-feature
# Create PR to develop on GitHub
```

### 2. Release Process
```bash
# 1. Merge develop to main
git checkout main
git pull origin main
git merge develop
git push origin main

# 2. Test in staging

# 3. Merge main to production
git checkout production
git pull origin production
git merge main
git push origin production

# 4. Deploy to production
```

### 3. Hotfix Process
```bash
# Create hotfix from production
git checkout production
git pull origin production
git checkout -b hotfix/critical-fix

# Fix issue
git add .
git commit -m "Fix critical issue"

# Merge to production
git checkout production
git merge hotfix/critical-fix
git push origin production

# Also merge to main and develop
git checkout main
git merge hotfix/critical-fix
git push origin main

git checkout develop
git merge hotfix/critical-fix
git push origin develop
```

## Environment Mapping

| Branch | Environment | URL | Auto Deploy |
|--------|------------|-----|-------------|
| `develop` | Development | dev.domain.com | Yes |
| `main` | Staging | staging.domain.com | Yes |
| `production` | Production | domain.com | Manual |

## Branch Protection Rules

### For `main`:
- Require pull request reviews (1 reviewer)
- Dismiss stale PR approvals
- Require status checks (tests, linting)
- No force pushes
- No deletions

### For `production`:
- Require pull request reviews (2 reviewers)
- Require code owner reviews
- Dismiss stale PR approvals
- Require all status checks
- Require branches to be up to date
- No force pushes
- No deletions
- Require signed commits

## Commit Message Convention

Use conventional commits for clear history:

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `style:` Code style (formatting, etc)
- `refactor:` Code refactoring
- `test:` Tests
- `chore:` Maintenance
- `security:` Security improvements

Examples:
```
feat: add support for Whisper model
fix: resolve audio conversion issue for M4A files
docs: update API documentation
security: implement rate limiting on API endpoints
```

## Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Security update
- [ ] Documentation update

## Testing
- [ ] Tested locally
- [ ] Unit tests pass
- [ ] Integration tests pass

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No sensitive data exposed
```

## Version Tagging

Use semantic versioning:
- `v1.0.0` - Major release
- `v1.1.0` - Minor release (new features)
- `v1.1.1` - Patch release (bug fixes)

```bash
# Tag a release
git tag -a v1.0.0 -m "Initial production release"
git push origin v1.0.0
```

## CI/CD Integration

Configure GitHub Actions for:
1. Run tests on PR to `develop`
2. Run security scans on PR to `main`
3. Deploy to staging on merge to `main`
4. Manual approval for production deployment

## Security Notes

⚠️ **NEVER commit to `production` directly**
⚠️ **NEVER commit secrets or API keys**
⚠️ **Always use .env files for configuration**
⚠️ **Rotate exposed credentials immediately**

---

This branching strategy ensures code quality, security, and stable deployments.