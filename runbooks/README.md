# Sema4.ai Runbook Templates

The Runbook templates here are used to help you get started in writing you Agents visible in Studio

The tooling and maintence in here allows us to add/update/remove runbook templates available for our tooling via Sema4.ai CDN.

[runbook-from-scratch.md](runbook-from-scratch.md) is the default runbook shown to Studio user when there is no Runbook defined, others are shown to the user separately.

> When adding new templates, make sure the [manifest.json](manifest.json) is up to date.
> `[DEPRECATED]` The `"type": "from-scratch"` must only be defined on one.

## Deployment

1. Run GitHub Action: [Runbook Templates - Update to S3](https://github.com/Sema4AI/gallery/actions/workflows/runbooks_s3_update.yml)
2. Re-start Studio and check the templates in Studio.
