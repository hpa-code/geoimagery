# Security Policy

## Supported Versions

Only the latest minor release is actively supported with security
patches. Older versions may receive fixes at the maintainer's
discretion.

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Instead, use GitHub's private vulnerability reporting:

1. Go to the [Security tab](https://github.com/hpa-code/geoimagery/security/advisories/new)
   of the repository.
2. Click **Report a vulnerability**.
3. Fill in as much detail as you can: affected versions, reproduction
   steps, suspected impact.

Alternatively, email **hacharya@u.rochester.edu** with the subject line
`[geoimagery security]`.

## What to expect

- We will acknowledge your report within **5 business days**.
- We will provide a more detailed response within **10 business days**,
  including an initial assessment and likely timeline for a fix.
- We will keep you informed as we work on a fix and coordinate
  disclosure.
- Once a fix is released, we will credit you in the changelog and
  release notes (unless you prefer to remain anonymous).

## Scope

This policy covers vulnerabilities in the `geoimagery` package itself.

For vulnerabilities in upstream dependencies (e.g.,
`earthengine-api`, `geemap`, `geopandas`, `rasterio`), please report
them to the relevant project. Please still let us know so we can pin
or patch around them.
