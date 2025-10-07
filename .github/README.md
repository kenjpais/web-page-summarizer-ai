# GitHub Configuration

This directory contains GitHub-specific configuration files for the release-page-summarizer project.

## Directory Structure

```
.github/
├── ISSUE_TEMPLATE/          # Issue templates
│   ├── bug_report.yml      # Template for bug reports
│   └── security_vulnerability.yml  # Template for security issues
├── prompts/                 # AI prompt templates
│   ├── bug-review.prompt.yml    # Prompts for bug review
│   └── feature-review.prompt.yml # Prompts for feature review
└── workflows/               # GitHub Actions workflows
    ├── ci.yml              # Continuous Integration pipeline
    └── issue-management.yml # Issue triage and management workflow
```

## Workflows

### Issue Management (`issue-management.yml`)
Handles all issue-related automation:
- Initial issue triage and classification
- Quality checks and validation
- AI-powered issue assessment
- Label management

### CI Pipeline (`ci.yml`)
Handles continuous integration tasks.

## Issue Templates
- **Bug Report**: Template for reporting bugs with required information
- **Security Vulnerability**: Template for reporting security issues

## AI Prompts
- **Bug Review**: Prompts for AI to assess bug reports
- **Feature Review**: Prompts for AI to assess feature requests

## Labels
The repository uses the following label categories:
- `kind/*`: Issue type (bug, feature, security, etc.)
- `status/*`: Issue status (needs-info, ready, etc.)
- `priority/*`: Issue priority (high, medium, low)