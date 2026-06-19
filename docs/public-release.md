# Public Release

Before making the repository or images public:

- Run `dagger call publication-gate --source=. --upstream-ref=devel`.
- Review `NOTICE` and `THIRD_PARTY_NOTICES.md`.
- Confirm built images preserve upstream AWX license and revision metadata.
- Confirm no official branding, logos, or support claims are present.
- Confirm publication is intentional and manually approved.

Use "unofficial AWX proof-of-concept image" or "AWX POC image" when describing
the output.
