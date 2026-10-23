# CTEAS-next remaining long scientific Actions (2026-10-23)

Eight more long-timeout original scientific workflows now use explicit `workflow_dispatch` rather than automatic PR/push runs. For workflows that used PR event HEAD to select source, required dispatch input `head_sha` provides an exact reviewed candidate SHA. Jobs, test steps, numerical thresholds, and timeouts are preserved. Completed workflow run SHA and the checked-out input SHA MUST be independently checked; merely providing `head_sha` does not constitute evidence of execution or science pass.

The three Issue54 workflows containing event-dependent PR-only synthetic jobs intentionally retain their path-limited pull_request triggers. Removing those triggers would silently skip existing positive/negative software admission tests; separating those jobs requires its own reviewed semantic change, not an automatic text deletion. All normal `repository-admission` and `scientific-admission` checks stay automatic and mandatory. Current Draft research PRs remain Draft and scientific NOT_RUN cannot be reinterpreted as PASS.

Changed workflows:

- `issue42-s3b1-huoshan-real-geo.yml`
- `issue46-p3-d2-wolsong-real.yml`
- `s2d-p7-pr-science.yml`
- `s2g-nonhefei-site-contract.yml`
- `s2g1bb2-real-noaa-p5-surf.yml`
- `s3d-noaa-archived-offline.yml`
- `s3d-noaa-to-native-p4-p7-science.yml`
- `s3f-real-noaa-multiyear-station.yml`
