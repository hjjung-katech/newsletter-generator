# GitHub Actions Workflows

This directory contains the consolidated CI/CD workflows for the Newsletter Generator project.

## 🔧 Active Workflows

### 1. `main-ci.yml` - Main CI Pipeline
**Triggers**: Push to main/develop/feature/fix branches, Pull requests to main/develop
**Purpose**: Comprehensive CI pipeline with multiple stages
**Stages**:
- **Code Quality & Security**: Formatting, linting, type checking, basic security scan
- **Unit Tests**: Multi-platform testing (Ubuntu, Windows) with Python 3.10, 3.11, 3.12
- **Mock API Tests**: Testing with mocked external APIs, including web mail tests
- **Integration Tests**: Real API testing (main/develop branches only)
- **Test Reports**: Consolidated test results and coverage reports
- **Build Check**: Package building and PyInstaller executable testing

**Key Features**:
- Multi-platform support (Ubuntu, Windows)
- Comprehensive test coverage with proper mocking
- Build verification for both wheel packages and Windows executables
- Automatic test result reporting

### 2. `deployment.yml` - Deployment Pipeline
**Triggers**: Push to main, Daily schedule (8 AM KST), Manual dispatch
**Purpose**: Newsletter generation and deployment
**Jobs**:
- **Generate Newsletter**: Creates newsletter with real APIs or demo content
- **GitHub Pages**: Automatic deployment to GitHub Pages
- **Railway Deployment**: Optional deployment to Railway platform
- **Notifications**: Slack notifications for success/failure

**Key Features**:
- Supports both real API and demo modes
- Automatic fallback to demo content when API keys unavailable
- GitHub Pages deployment for newsletter hosting
- Optional Railway deployment with smoke tests

### 3. `security-scan.yml` - Security Scanning
**Triggers**: Weekly schedule (Monday 2 AM UTC), Manual dispatch
**Purpose**: Comprehensive security scanning
**Scans**:
- **Secret Detection**: detect-secrets baseline scanning
- **Python Security**: Bandit security linting and Safety vulnerability checks
- **Filesystem Scan**: Trivy vulnerability scanning
- **Docker Security**: Container image security scanning (optional)
- **Dependency Review**: GitHub native dependency vulnerability checks

**Key Features**:
- Weekly automated security audits
- Multiple security tools integration
- SARIF upload to GitHub Security tab
- Comprehensive security reporting

## 🗑️ Removed Workflows

The following workflows were removed due to redundancy or obsolescence:

- `ci.yml` - Replaced by `main-ci.yml` (more comprehensive)
- `code-quality.yml` - Integrated into `main-ci.yml` quality-checks stage
- `email-tests.yml` - Integrated into `main-ci.yml` mock-api-tests stage
- `test-tools.yml` - Specific tool testing replaced by comprehensive approach
- `newsletter.yml` - Replaced by `deployment.yml` (enhanced functionality)
- `ci-improved.yml`, `pr-checks.yml`, `nightly.yml`, `release.yml` - Experimental workflows

## 🎯 Workflow Strategy

### CI/CD Pipeline Design
1. **Quality Gates**: All changes must pass code quality and security checks
2. **Multi-Platform Testing**: Ensure compatibility across different operating systems
3. **Staged Testing**: Unit → Mock API → Integration testing progression
4. **Build Verification**: Verify both development and production builds
5. **Deployment Automation**: Automatic deployment for main branch changes

### Test Strategy
- **Unit Tests**: Fast, isolated component testing
- **Mock API Tests**: Integration testing without external dependencies
- **Integration Tests**: Real API testing for critical paths
- **Build Tests**: Verify packaging and executable creation

### Security Strategy
- **Continuous Security**: Basic security checks in every CI run
- **Deep Security**: Weekly comprehensive security audits
- **Multi-Tool Approach**: Multiple security scanning tools for comprehensive coverage
- **Automated Reporting**: Integration with GitHub Security tab

## 📊 Workflow Performance

### Optimization Features
- **Caching**: Pip cache, dependency cache for faster builds
- **Parallel Execution**: Independent jobs run in parallel
- **Fail-Fast Strategy**: Quick feedback on critical failures
- **Conditional Execution**: Skip expensive tests when not needed
- **Artifact Management**: Proper artifact storage and cleanup

### Resource Management
- **Concurrency Control**: Prevent concurrent runs on same branch
- **Timeout Management**: Prevent stuck workflows
- **Selective Triggers**: Path-based and branch-based triggering
- **Matrix Strategy**: Efficient multi-platform testing

## 🚀 Usage Guidelines

### For Developers
1. **Feature Development**: All changes automatically tested via `main-ci.yml`
2. **Pull Requests**: Full CI pipeline runs on PR creation/updates
3. **Security**: Weekly security scans provide security insights
4. **Builds**: Windows executable builds tested automatically

### For Maintainers
1. **Manual Newsletter**: Use `deployment.yml` manual dispatch
2. **Security Audits**: Review weekly security scan results
3. **Build Issues**: Check Windows build artifacts for debugging
4. **Test Reports**: Monitor test coverage and failure trends

### Environment Variables Required
- **CI Testing**: Mock keys automatically provided
- **Integration Tests**: Real API keys in repository secrets
- **Deployment**: API keys required for real newsletter generation
- **Notifications**: SLACK_WEBHOOK for deployment notifications

## 📊 Performance Metrics & Goals

| 측정 항목 | 목표 | 현재 상태 |
|---------|------|----------|
| 전체 CI 시간 | < 5분 | ~3-4분 |
| PR 피드백 시간 | < 2분 | ~1-2분 |
| 테스트 커버리지 | > 70% | 진행중 |
| 빌드 성공률 | > 95% | 모니터링중 |
| 보안 취약점 | 0개 | 주간 검사 |

## 🛠️ Required GitHub Secrets

### CI/CD Testing
```
# Mock keys automatically provided for CI
OPENAI_API_KEY=test-key
SERPER_API_KEY=test-key
GEMINI_API_KEY=test-key
```

### Integration Tests (Optional)
```
OPENAI_API_KEY          # Real OpenAI API key
SERPER_API_KEY          # Real Serper API key
GEMINI_API_KEY          # Real Google Gemini API key
ANTHROPIC_API_KEY       # Real Anthropic API key
POSTMARK_SERVER_TOKEN   # Email service token
EMAIL_SENDER            # Verified sender email
TEST_EMAIL_RECIPIENT    # Test email recipient
```

### Deployment
```
RAILWAY_TOKEN           # Railway deployment (optional)
SLACK_WEBHOOK           # Slack notifications (optional)
```

## 🔧 Maintenance

### Regular Tasks
- Review security scan results weekly
- Monitor test failure trends
- Update dependency versions
- Review and optimize workflow performance
- Check build artifact quality
- Validate cross-platform compatibility

### Troubleshooting
- Check workflow logs for detailed error information
- Review test artifacts for debugging
- Verify environment variable configuration
- Check PyInstaller build issues in build artifacts
- Monitor resource usage and optimization opportunities

### Branch Protection Rules (Recommended)
```yaml
# Require status checks before merging
required_status_checks:
  - "Code Quality & Security"
  - "Unit Tests - ubuntu-latest (3.10)"
  - "Mock API Tests"

# Require branches to be up to date
require_branches_up_to_date: true

# Include administrators
enforce_admins: true
```
