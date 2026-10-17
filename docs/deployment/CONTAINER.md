# Container packaging — portable C++20 research subset

**Status: PORTABLE_SOFTWARE_VALIDATED** for Linux AMD64/ARM64 by
[GitHub Actions run #38995287227](https://github.com/RRain001/CTEAS-next/actions/runs/38995287227).
Both architecture jobs built the container, executed the portable C++/Python
and G5 headless checks, constructed the minimal runtime image, checked the
runtime architecture and 11 executable entrypoints, verified non-root startup,
and uploaded software regression evidence. This packaging change does not re-certify the
original 143-hour scientific workflows and does not add any physical formulas.

## Build and inspect locally

Prerequisites: Docker with BuildKit and network access to base images and
Debian/PyPI packages. From the CTEAS-next repository root:

```sh
docker build --file docker/cpp/Dockerfile --target runtime \
  --tag cteas-next:portable .
docker run --rm cteas-next:portable
```

The first stage runs the existing nine standalone CMake Debug builds and
explicit portable CTests, the scoped P4/P5/G5 Python unittest directories,
and G5 offscreen/fail-closed smoke test. Logs are retained in the **verification
build stage**, not in the runtime image. To retrieve them:

```sh
docker build --file docker/cpp/Dockerfile --target verification \
  --tag cteas-next:verification .
id=$(docker create cteas-next:verification)
docker cp "$id:/tmp/cteas-software" ./local-cteas-software-evidence
docker cp "$id:/tmp/cteas-python" ./local-cteas-python-evidence
docker rm "$id"
```

Both `local-cteas-*-evidence` paths must be kept out of commits. These
software regressions are not a complete P1–P7 end-to-end simulation; the
migrated full C1/C2 143h workflows remain NOT_RUN here.

## Run with controlled scientific input/output paths

```sh
mkdir -p cases results
docker run --rm --user "$(id -u):$(id -g)" \
  --mount type=bind,src="$PWD/cases",dst=/cases,readonly \
  --mount type=bind,src="$PWD/results",dst=/results \
  cteas-next:portable cteas_p7_calmet21_inspect /cases/<input-file>
```

Replace the example program arguments with the selected standalone program's
actual CLI contract. The example is a pattern, **not an accepted generic P7
simulation command**. The runtime image contains 11 explicitly selected P1–P7
tools only, not the complete test executables or all physics option branches.
All calculation inputs must be explicitly provided and validated.

## Platform-specific Python dependency gate

The original repository pins `PySide6==6.11.0`, which was available to the
Linux AMD64 builder but unavailable for Linux ARM64 in the first CI run
`38994611583`. The Docker verification stage therefore **keeps the upstream
`requirements.txt` unchanged** and replaces only the ARM64 Qt wheel pin with
`PySide6==6.8.0.2`. The substitution is explicit and checked during build;
this tests bounded G5 headless software behavior, **not GUI-version numerical
or interface equivalence**. AMD64 keeps the upstream 6.11.0 pin. Both stages
install Debian's `libglib2.0-0`, needed by the PySide6 module loader.

Previous failed container run: [CI #38994611583](https://github.com/RRain001/CTEAS-next/actions/runs/38994611583):
AMD64 completed C++ and Python portable tests before a missing GLib shared
library prevented Qt smoke; ARM64 failed resolving PySide6 6.11.0. No C++
numeric failure was established. The corrected build must pass CI separately.

## Platform and image policy

- The base is multi-architecture `python:3.11-slim-bookworm`; Docker publishes
  a Linux container image. macOS hosts can run Linux containers through Docker
  Desktop, but this does **not** prove native macOS C++ compilation.
- `.github/workflows/docker-portable.yml` uses native hosted Linux AMD64 and
  ARM64 runners to build and validate separate architecture images, including
  explicit non-root smoke tests. It does **not** automatically publish an
  unvalidated public container registry artifact.
- After both matrix legs are green, a separately reviewed publishing change can
  pin the base image digest, publish a multiarch GHCR manifest from verified
  immutable tags and add version/SBOM metadata. `docker buildx build --platform
  linux/amd64,linux/arm64` is possible but must not bypass these gates.
- The final image holds tested **Debug** binaries. A production optimized
  Release variant must get its own compilation and numerical-regression gates.

## External assets and privacy boundaries

No original CALMET/CALPUFF Fortran, CGIAR SRTM crop, bundled fonts, Git history,
or frozen project reference outputs are copied from the builder to the runtime
image. `.dockerignore` additionally refuses the excluded local third-party
paths even if they were restored on a developer workstation. Input and output
data are **never** baked into the published runtime stage.

Restoration of legally authorized vendor assets for historical comparisons must
be a separately controlled, locally audited workflow. Container runtime alone
does not establish any redistribution permissions.

P6/P7 only reconstruct selected scientific branches. In particular,
`MWET>0` and wet deposition are unaccepted, and G5 generic
`met`/`puff`/`all` remain fail-closed. See
`docs/migration/SCIENTIFIC_RERUN_PLAN.md`.

## Verification and current limitations

The CTest selection explicitly comprises 33 portable software tests, and the
Python discovery is limited to P4/P5 data preparation and G5, with one
vendor-dependent test omitted (historically 73 selected PASS). The newly completed
Docker [CI run #38995287227](https://github.com/RRain001/CTEAS-next/actions/runs/38995287227)
provides the architecture-specific software results; its success does not
replace full C1/C2 scientific reruns or expand physics option acceptance.

Neither `Dockerfile` nor the CI workflow mutates P1–P7 numerical implementation.
