#include "cteas/geo/source_inputs.hpp"
#include <gdal_priv.h>
#include <ogr_spatialref.h>
#include <cmath>
#include <fstream>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
namespace cteas::reconstruction::geo {
namespace { using DatasetPtr = std::unique_ptr<GDALDataset, decltype(&GDALClose)>; }

GeographicBounds read_bbox(const std::filesystem::path& path) {
  std::ifstream in(path);
  if (!in) throw std::runtime_error("P1: cannot open bbox: " + path.string());
  std::string line;
  while (std::getline(in, line)) {
    const auto pos = line.find_first_not_of(" \t\r");
    if (pos == std::string::npos || line[pos] == '#') continue;
    std::istringstream row(line);
    GeographicBounds b;
    std::string extra;
    if (!(row >> b.west_deg >> b.south_deg >> b.east_deg >> b.north_deg) ||
        (row >> extra) || !std::isfinite(b.west_deg) || !std::isfinite(b.east_deg) ||
        !std::isfinite(b.south_deg) || !std::isfinite(b.north_deg) ||
        b.west_deg < -180 || b.east_deg > 180 ||
        b.south_deg < -90 || b.north_deg > 90 ||
        b.west_deg >= b.east_deg || b.south_deg >= b.north_deg)
      throw std::runtime_error("P1: invalid bbox record");
    return b;
  }
  throw std::runtime_error("P1: bbox missing numeric record");
}

TerrainRaster read_srtm_geotiff(const std::filesystem::path& path) {
  GDALAllRegister();
  DatasetPtr ds(static_cast<GDALDataset*>(GDALOpen(path.string().c_str(), GA_ReadOnly)), &GDALClose);
  if (!ds) throw std::runtime_error("P1: GeoTIFF open failed: " + path.string());
  if (ds->GetRasterCount() != 1 || ds->GetRasterXSize() < 1 || ds->GetRasterYSize() < 1)
    throw std::runtime_error("P1: expected one nonempty elevation band");
  const auto* driver = ds->GetDriver();
  if (!driver || std::string(driver->GetDescription()) != "GTiff")
    throw std::runtime_error("P1: expected a GeoTIFF source");
  GDALRasterBand* band = ds->GetRasterBand(1);
  if (band->GetRasterDataType() != GDT_Int16)
    throw std::runtime_error("P1: expected native int16 elevation source");
  int has_nodata = 0;
  const double nodata = band->GetNoDataValue(&has_nodata);
  if (!has_nodata || !std::isfinite(nodata) || nodata < -32768 || nodata > 32767 ||
      std::trunc(nodata) != nodata)
    throw std::runtime_error("P1: missing/invalid int16 NoData metadata");
  double transform[6]{};
  if (ds->GetGeoTransform(transform) != CE_None)
    throw std::runtime_error("P1: GeoTIFF lacks geotransform");
  for (double value : transform)
    if (!std::isfinite(value)) throw std::runtime_error("P1: nonfinite geotransform");
  const OGRSpatialReference* srs = ds->GetSpatialRef();
  if (!srs || srs->IsEmpty() || !srs->IsGeographic())
    throw std::runtime_error("P1: elevation crop must have geographic CRS");
  OGRSpatialReference expected_wgs84;
  if (expected_wgs84.SetWellKnownGeogCS("WGS84") != OGRERR_NONE ||
      !srs->IsSameGeogCS(&expected_wgs84))
    throw std::runtime_error("P1: source GeoTIFF CRS must be WGS84 geographic");
  const int nx = ds->GetRasterXSize(), ny = ds->GetRasterYSize();
  const cteas::atmos::Shape2D shape(nx, ny);
  TerrainRaster result{cteas::atmos::Array2D<std::int16_t>(shape),
                       cteas::atmos::ValidityMask2D(shape), {},
                       std::string(ds->GetProjectionRef()), static_cast<std::int16_t>(nodata)};
  for (int i = 0; i < 6; ++i) result.geo_transform[static_cast<std::size_t>(i)] = transform[i];
  if (band->RasterIO(GF_Read, 0, 0, nx, ny, result.raw_elevation_m.data(), nx, ny,
                     GDT_Int16, 0, 0, nullptr) != CE_None)
    throw std::runtime_error("P1: raster reading failed");
  for (int j = 0; j < ny; ++j)
    for (int i = 0; i < nx; ++i)
      if (result.raw_elevation_m(static_cast<std::size_t>(i), static_cast<std::size_t>(j)) != result.no_data)
        result.valid.set_valid(static_cast<std::size_t>(i), static_cast<std::size_t>(j));
  return result;
}
}  // namespace cteas::reconstruction::geo
