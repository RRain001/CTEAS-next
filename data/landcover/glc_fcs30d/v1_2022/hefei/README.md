# Hefei 2022 GLC_FCS30D acquisition — Issue #51

Data acquisition only. No P2/P3/P6 physics, historical GLCC case or science
acceptance status is changed. This land-cover product is a classified satellite
map, not independently measured local validation of CTEAS-next physics.

## Files and verified content

- `hefei_2022_30m.tif`: real Earth Engine download, single-band uint8 GeoTIFF,
  172 × 172 pixels, EPSG:32650, 30 × 30 m, 6,168 bytes.
- `metadata.json`: source tile, grid hash, exact geometry, histogram, repeat
  comparison, package versions, download UTC time and script fingerprint.
- `ATTRIBUTION.md`: authors, dataset/publication DOI, mirror version and license.

SHA256: `340d224d961c88637363be9616302bdf6b955b4921144edc814b875ef9798473`.
All 29,584 pixels are classified; NoData/fill fraction is 0. Twelve observed
codes: 10, 11, 20, 52, 62, 72, 130, 182, 183, 190, 200, 210. Full counts are in
metadata. Allowed classes follow the linked community catalog; 0 and 250 are
explicit fill codes, excluded from classified counts. GeoTIFF NoData is 0.

The unchanged frozen grid has XREFKM=510.885, YREFKM=3531.269,
DGRIDKM=0.1 and NX=NY=50. Domain bounds in metres are
[510885, 3531269, 515885, 3536269]; buffered request bounds are
[510825, 3531209, 515945, 3536329]. Actual pixel-aligned raster bounds are
[510810, 3531180, 515970, 3536340], covering the entire buffer.
The source has one intersecting tile, `GLC_FCS30D_20002022_E115N35_Annual`.
Two independently generated download requests produced identical file hashes,
arrays, masks, transforms and class histograms. No byte-level discrepancy
requires explanation.

## Reproduce on Mac (explicit online operation)

From the repository root, create an independent environment (Python >=3.11):

```sh
python3 -m venv /private/tmp/cteas-ee-issue51-venv
/private/tmp/cteas-ee-issue51-venv/bin/python -m pip install earthengine-api rasterio pyproj requests
```

For first-time authentication, run `ee.Authenticate(auth_mode='localhost')`
in that Python environment and complete Google OAuth yourself in the browser.
Then the downloader calls `ee.Initialize(project='cteas-earthengine')` and
reuses local credentials. Never paste authentication output into GitHub.
The actual local run used these sanitized commands:

```sh
/private/tmp/cteas-ee-issue51-venv/bin/python scripts/s2g/glc_fcs30d_acquire.py download
/private/tmp/cteas-ee-issue51-venv/bin/python scripts/s2g/glc_fcs30d_acquire.py verify
/private/tmp/cteas-ee-issue51-venv/bin/python -m unittest scripts.s2g.tests.test_glc_fcs30d_acquisition -v
```

The committed directory already exists; a reproduction must use a **new**
`--directory /private/tmp/hefei-glc-reproduction` to avoid overwriting it.
The downloader never authenticates automatically, records no signed URLs, and
suppresses sensitive API exception payloads. Requests above 32 MiB or API
limits fail clearly; chunked exports are not implemented. Offline `verify`
and unittest need numpy/rasterio/pyproj only, no Earth Engine import, Google
credentials or network. No default CI network job is added.

Acceptance here covers the delivered file and provenance only. The mutable
community mirror is identified and the received crop is SHA-pinned; this is
not an independent checksum comparison with the full upstream Zenodo archive.
