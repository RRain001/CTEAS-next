# Data attribution and reuse

GLC_FCS30D regional extract, 2022, from **Zenodo v1 (2023)** via the
Earth Engine Community Catalog (`v1-community-gee`). This is not Zenodo v2.

Creators: Liangyun Liu, Xiao Zhang and Tingting Zhao (2023).
GLC_FCS30D: the first global 30-m land-cover dynamic monitoring product with
fine classification system from 1985 to 2022. Zenodo.
Dataset DOI: https://doi.org/10.5281/zenodo.8239305

Scientific publication: Zhang, X., Zhao, T., Xu, H., Liu, W., Wang, J.,
Chen, X. and Liu, L. (2024). GLC_FCS30D: the first global 30 m land-cover
dynamics monitoring product with a fine classification system for the period
from 1985 to 2022 generated using dense-time-series Landsat imagery and the
continuous change-detection method. Earth System Science Data, 16, 1353–1381.
https://doi.org/10.5194/essd-16-1353-2024

Community mirror curator: Samapriya Roy; catalog reports last GEE update
2024-02-20. Source, classification table and license declaration:
https://gee-community-catalog.org/projects/glc_fcs/

License: **CC BY 4.0**, https://creativecommons.org/licenses/by/4.0/ .
Retain attribution and indicate modifications when reusing this extract.
No endorsement by the creators or curator is implied.

Changes made for CTEAS-next: select annual `b23` (2022), mosaic intersecting
tiles in ascending `system:index` order (last valid pixel wins), crop to the
frozen Issue #160 Hefei 20 km domain plus 60 m buffer, and reproject to WGS84/UTM zone 50N
at 30 m using Earth Engine's default nearest-neighbour sampling. No category
remapping or interpolation to fractional classes. Pixel-aligned export edges
extend slightly beyond the requested buffer. Only this small regional extract
is redistributed; the global dataset is not included.

License and attribution checked on 2026-10-20 against the upstream Zenodo v1
record and GEE Community Catalog. Both declare CC BY 4.0. This permits
redistribution of this extract with attribution, a license link and disclosure
of the crop/reprojection changes above. No endorsement is implied.
