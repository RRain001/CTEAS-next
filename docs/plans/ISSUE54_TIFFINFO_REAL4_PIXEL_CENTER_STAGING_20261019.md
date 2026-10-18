# #54 P1: original TERREL GeoTIFF center-coordinate REAL*4 staging

## Source-based hypothesis (no tolerance changes)

The identical-SHA genuine SRTM90m and SRTMGL1 30m direct original/native
pixel-lineage runs in [#54](https://github.com/RRain001/CTEAS-next/issues/54)
showed accepted grid-cell disagreements, often clustered in one axis.
The previous C++ implementation rounded `(double_origin + double_step/2)`
**once** to float. But untouched TERREL 7.0.0
`TIFFINFO.FOR GET_IFD` has separate assignments:

```fortran
dxi = val8(1)              ! destination default REAL*4
dyi = val8(2)
xorg = sngl(val8(4))       ! source ModelTiepoint -> REAL*4 first
yorg = sngl(val8(5))
...                       ! xmul=1 for supported WGS84 geographic source
dyi = abs(dyi)
if (iorienti.eq.1) dyi = -dyi
if (lpixel) then           ! RasterPixelIsArea
  xorg = xorg+dxi/2.
  yorg = yorg+dyi/2.
endif
```

`terrel.for LOADTIFF` then computes `xc=xorg+dxi*(i-1)` and
`yc=yorg+dyi*(j-1)` and passes them through `GLOBE` and `CELLIND`.

This PR reproduces the **operation sequence**, not a fitted coordinate
offset. Other projection, grid, data, averages, NoData or format logic is
unchanged. Scope: north-up WGS84 **PixelIsArea** single-band integer TIFF.
If the source GeoTIFF uses PixelIsPoint or a nonzero tiepoint index,
it needs separate auditable admission; do not claim coverage here.

## Verification contract

- PR CI: existing #54 D1 C++ GDAL synthetic tests, with new 30m and 90m
  REAL*4 reference-expression regressions; separate D1B synthetic source
  adapter checks.
- **Real science ONLY through owner-authorized manual main workflow**:
  90m/30m use unchanged original TERREL, same exact losslessly repackaged
  TIFF SHA for original and C++, exact per-cell SAV hits,
  1e-5m unrounded-mean bound and F8.1 DAT bound.
- Check historical Hefei frozen P1 regression, including original 90x77
  reference and the main C++ wrapper, before declaring broad regression
  safety. Synthetic tests alone are insufficient.
- If either real route still fails, do not broaden numerical tolerance or
  alter DEM; the next instrumented comparison must isolate remaining
  stages (pixel center, PROJ vs COORDLIB, float32 CELLIND).

Until independently observed, D2/D3 original scientific parity remains
`NUMERIC_FAIL`, D4 `NOT_ACCEPTED`, and Issue #54 stays open.
