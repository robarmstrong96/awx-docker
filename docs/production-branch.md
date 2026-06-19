# Production Branch

`development` is the integration branch. It may build moving upstream AWX refs
such as `devel`.

`production` is the promotion branch. It builds only the pinned revision in
`awx.lock.yml`.

## Promotion Flow

1. Run the image pipeline on `development`.
2. Review the generated evidence.
3. Run `dagger call promote-candidate --source=. --upstream-ref=devel`.
4. Open a pull request targeting `production`.
5. Wait for `Project Checks` and `Production Admission`.
6. Merge only after the lock and publication gate checks pass.

## Branch Protection

The `production` branch is protected with:

- pull requests required before merge
- one approving review required
- stale approvals dismissed after new pushes
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

`Production Pipeline / Build locked image` is intentionally not a required
merge check yet. It remains available as the post-merge locked-image build.
