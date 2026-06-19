# Production Branch

`development` is the integration branch. It may build moving upstream AWX refs
such as `devel`.

`production` is the promotion branch. It builds only the pinned revision in
`awx.lock.yml`.

## Promotion Flow

1. Run the image pipeline on `development`.
2. Review the generated evidence.
3. Run `dagger call promote-candidate --source=. --upstream-ref=devel`.
4. Fill in `promotion.promoted_by` and either `promotion.evidence_run_url` or
   `promotion.evidence_waiver` in `awx.lock.yml`.
5. Open a pull request targeting `production`.
6. Wait for `Project Checks` and `Production Admission`.
7. Merge only after the lock and publication gate checks pass.

## Branch Protection

The `production` branch is protected with:

- pull requests required before merge
- conversation resolution required
- required branches to be up to date
- linear history required
- force pushes disabled
- branch deletion disabled
- admin enforcement enabled

Required checks:

- `Code quality`
- `Policy tests`
- `Validate production lock`
- `Publication gate`

The production `Publication gate` check reads `awx.lock.yml`; it does not
evaluate a floating upstream branch.

`Production Pipeline / Publish locked image` is intentionally not a required
merge check. It runs after production updates and publishes the locked image as
both `production` and `latest`.
