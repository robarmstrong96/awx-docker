# Upstream Health

`dagger call upstream-health --source=. --awx-ref=devel` checks GitHub commit
status and check-run signals for the resolved upstream AWX ref.

Decision states:

- `pass`: observed signals are acceptable
- `warn`: weak or missing signal is allowed by the selected mode
- `wait`: upstream checks are still pending
- `fail`: upstream exposed a failing or blocked signal
- `unknown`: signals could not be collected
- `waived`: reserved for future human overrides

Modes are configured in `policies/upstream-health.yml`:

- `scheduled-build`
- `local`
- `publication`

Evidence is written under `build/evidence/` when the Python CLI runs locally.
Dagger functions return evidence directories where practical.
