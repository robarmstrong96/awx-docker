# Upstream Health

`dagger call upstream-health --source=. --upstream-ref=devel` checks provider
signals for the resolved upstream ref.

Provider selection:

- `auto`: use GitHub checks for `github.com` repositories, otherwise use generic Git
- `github`: require a `github.com` repository and evaluate GitHub check runs
- `generic-git`: resolve the ref only; no CI health signal is available
- `file`: read normalized provider signals from `--signal-file`

Decision states:

- `pass`: observed provider signals are acceptable
- `warn`: weak or missing signal is allowed by the selected mode
- `wait`: upstream checks are still pending
- `fail`: upstream exposed a failing or blocked signal
- `unknown`: signals could not be collected
- `waived`: reserved for future human overrides

Modes are configured in `policies/upstream-health.yml`:

- `scheduled-build`
- `local`
- `publication`

GitHub check classification:

- failing build-like checks block; examples include `Build`, `Container build`,
  `Image build`, `Docker build`, and `buildx`
- failing SonarCloud, lint, static-analysis, or docs checks are retained as
  non-blocking evidence
- missing CI or missing build-success evidence warns for `local` and
  `scheduled-build`, but fails for `publication`

Evidence is written under `build/evidence/` when the Python CLI runs locally.
Dagger functions return evidence directories where practical.

GitHub raw API responses are audit evidence only and are written under
`build/evidence/upstream/raw/github/`.
