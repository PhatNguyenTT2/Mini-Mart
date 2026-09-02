# AIS-R2 source export tool

`export_v5_source_bundle.cjs` is the bounded database-facing edge for AIS-R2.
It opens `REPEATABLE READ READ ONLY` transactions against only the chat,
catalog, and order databases. It never reads the auth database or exports
names, phone numbers, addresses, account IDs, or other customer attributes.

The tool refuses to connect unless it receives an admitted, canonical
`catalog-audit/1.1` JSON file. Provenance and research-export rights must be
admitted before export. Language coverage may be
`PENDING_POST_EXPORT_AUDIT`, because the immutable 5,200-item projection is the
input to that audit; this status still blocks dataset admission and every model
run. The current project does not yet have the access receipt, so the command
below is a future command template rather than an authorization to execute:

```text
node ai-service-v2/tools/export_v5_source_bundle.cjs \
  --spec backend/docs/chatbot/seed-product/benchmark-spec-v5.json \
  --catalog-audit <admitted-catalog-audit.json> \
  --run-id <locked-ready-benchmark-run-id> \
  --source-commit <full-commit-sha> \
  --output-root <new-empty-source-bundle-root>
```

Remote PostgreSQL requires a CA file through `SUPABASE_DB_CA_PATH` or
`DB_SSL_CA_PATH`; insecure TLS is not supported. Existing output and staging
roots are rejected. The nine generator files must have the same Git-cleaned
blob identity as the declared commit; the manifest tree hashes the committed
blob bytes, so a clean Windows CRLF checkout remains equivalent to its LF Git
blob. A failed attempt is not retried in place.

The resulting six-file Source Bundle must still pass:

```text
ai-v2 materialize-v5-source <source-bundle> <new-canonical-snapshot>
ai-v2 assess-snapshot <canonical-snapshot>
```

Passing the exporter or fixture tests does not run a model, open TEST, or create
an Accepted Result Row.
