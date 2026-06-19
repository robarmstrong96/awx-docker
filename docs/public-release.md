# Public Release

Before making the repository or images public:

- Run `dagger call publication-gate --source=. --upstream-ref=devel`.
- For production promotion, run `dagger call production-admission --source=.`.
- For image publication or production promotion, the publication gate requires
  `image-verification.json` evidence from a verified image build.
- Development images publish with the `development` tag. Production images
  publish with `production` and `latest` tags.
- Review `NOTICE` and `THIRD_PARTY_NOTICES.md`.
- Confirm built images preserve upstream AWX license and revision metadata.
- Confirm no official branding, logos, or support claims are present.
- Confirm publication is intentional and manually approved.

Use "unofficial AWX proof-of-concept image" or "AWX POC image" when describing
the output.
