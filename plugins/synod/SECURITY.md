# Security Policy

## Supported Versions

| Version | Status | Supported Until |
|---------|--------|-----------------|
| 1.0.x   | Supported | Current release |
| < 1.0   | Unsupported | Not maintained |

Only the latest 1.0.x release receives security updates and patches.

## Reporting a Vulnerability

We take security seriously. If you discover a vulnerability, please report it responsibly using one of these methods:

### Preferred: GitHub Security Advisories

Use GitHub's private vulnerability disclosure feature:

1. Go to the [Security tab](https://github.com/quantsquirrel/claude-synod-debate/security) in the Synod repository
2. Click "Report a vulnerability"
3. Complete the vulnerability details form
4. Your report will be reviewed privately by the maintainers

### Alternative: Private Issue

If you cannot use GitHub Security Advisories:

1. Email your report to the project maintainers with details listed below
2. Mark your email subject line with `[SECURITY VULNERABILITY]`
3. Do not open a public issue for security vulnerabilities

## What to Include in Your Report

Please provide the following information to help us assess and address the vulnerability:

- **Description**: Clear explanation of the vulnerability
- **Affected Versions**: Which version(s) of Synod are affected
- **Severity**: Your assessment (Critical, High, Medium, Low)
- **Steps to Reproduce**: Detailed steps or proof of concept (if applicable)
- **Potential Impact**: What could happen if exploited
- **Suggested Fix**: Any proposed solution (optional but helpful)
- **Your Contact Information**: Name, email, and affiliation (for credit and follow-up)

## Response Timeline

We are committed to responding promptly to security reports:

- **48 hours**: Initial acknowledgment of your report
- **7 days**: Preliminary assessment and security impact evaluation
- **Ongoing**: Updates on progress toward a fix
- **Public Disclosure**: Coordinated timing after fix is released (see guidelines below)

## What NOT to Do

To protect users and maintain responsible disclosure practices:

- **Do not** publicly disclose the vulnerability before a fix is available
- **Do not** open a public issue or discussion about the vulnerability
- **Do not** post details on social media or public forums
- **Do not** attempt to exploit the vulnerability beyond proof-of-concept
- **Do not** contact users or downstream projects before we've released a fix

Violations of responsible disclosure practices may result in legal action.

## Security Best Practices

### When Using Synod

- Keep Synod updated to the latest 3.0.x version
- Review [CHANGELOG.md](./CHANGELOG.md) for security-related updates
- Report any suspicious behavior or potential vulnerabilities immediately

### For Contributors

- Never commit secrets or credentials to the repository
- Use environment variables for sensitive configuration
- Follow the security guidelines in [CONTRIBUTING.md](./CONTRIBUTING.md)

## Acknowledgments

We appreciate the security research community's responsible disclosure practices. Researchers who report valid vulnerabilities will be publicly acknowledged (with permission) in our release notes.

## Questions?

For general security questions or clarifications, open a public issue with the `[SECURITY]` label (without sharing vulnerability details).
