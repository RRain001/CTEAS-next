# Wolsong GLC_FCS30D 2022 attribution

Liangyun Liu, Xiao Zhang and Tingting Zhao (2023). GLC_FCS30D: the first
global 30-m land-cover dynamic monitoring product with fine classification
system from 1985 to 2022. Zenodo **v1**.
https://doi.org/10.5281/zenodo.8239305

Earth Engine Community Catalog mirror, curated by Samapriya Roy; catalog
reports GEE update 2024-02-20:
https://gee-community-catalog.org/projects/glc_fcs/ .
Asset: `projects/sat-io/open-datasets/GLC-FCS30D/annual`.
Version label: `v1-community-gee`; not the newer Zenodo v2.
License publicly declared by the catalog: **CC BY 4.0**,
https://creativecommons.org/licenses/by/4.0/ . Retain attribution and indicate
changes when reusing; no creator or curator endorsement is implied.

Changes: select 2022 annual band b23, mosaic intersecting source tiles in
ascending system:index order (last valid pixel wins), crop Wolsong 20×20 km
model domain plus 60 m buffer, and reproject to EPSG:32652 at nominal 30 m
using nearest-neighbour sampling. Pixel-aligned export bounds extend beyond
the buffer. No manual recoding, ocean filling or class replacement. Only this
small regional extract is redistributed, not the global dataset.

This is source acquisition, not validated coastal USGS52/55 classification
or P2/P3 numerical science acceptance. Upstream archive bytes were not
downloaded for an independent full-archive checksum comparison.
