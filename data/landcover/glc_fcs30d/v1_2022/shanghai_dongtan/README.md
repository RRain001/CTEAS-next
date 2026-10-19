# Shanghai Dongtan 2022 GLC_FCS30D coastal validation case — not yet downloaded

Candidate site: ~121.98°E, 31.52°N, east Chongming / Yangtze Estuary. Model UTM51N (EPSG:32651), SW origin (400.655 km, 3485.184 km), 50×50 grid at 100 m; verify the polygon overlaps both real land and sea before acceptance.

Current data state:
- Real 2022 GLC TIFF `shanghai_dongtan_2022_30m.tif`: **NOT YET ACQUIRED**.
- `metadata.json`: **NOT YET GENERATED**.
- Real Full GSHHG shoreline: official source verified in earlier Hefei run, project Release publishing remains a separate explicit step.
- **Do not** use this candidate site to claim real USGS52/55 classification PASS until all prerequisites and source audits succeed.
- Earth Engine source matches the Hefei 2022 product: `projects/sat-io/open-datasets/GLC-FCS30D/annual`, band b23, categorical nearest neighbour, CC BY 4.0.

Authenticated user-only download (Mac/Ubuntu):
```bash
python3 -m scripts.s2g.glc_fcs30d_shanghai_acquire download
python3 -m scripts.s2g.glc_fcs30d_shanghai_acquire verify
```
The downloader writes genuine small GeoTIFF, metadata, attribution. Review them and commit in a separate PR for real-source acceptance. Do not put Google Earth Engine tokens in GitHub; this checkout cannot access the user's Earth Engine authorization.

Once that real crop exists in main, the separate `workflow_dispatch` [Issue46 Shanghai Dongtan real 2022 coastal P2-B 52/55](../../../../.github/workflows/issue46-p2b-shanghai-real-coastal-2022.yml) can run. It independently requires coastline intersects the model grid, 35→38 per-cell area preservation, actual USGS52 and 55 water area both positive, no GLC NoData masking, source hash and model-grid provenance.

If GLC_FCS30D's marine pixels are unclassified (0/250), the real gate must fail closed. Never generate synthetic 210 to mimic ocean.
