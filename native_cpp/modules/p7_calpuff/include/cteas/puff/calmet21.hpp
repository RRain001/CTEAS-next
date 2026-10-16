#pragma once
#include <cstddef>
#include <cstdint>
#include <functional>
#include <string>
#include <vector>

namespace cteas::puff {
struct Calmet21Time {
    int year = 0, julian_day = 0, hour = 0, seconds = 0;
    std::int64_t unix_seconds = 0;
};
struct Calmet21Header {
    int nx = 0, ny = 0, nz = 0, irtype = 0, wind_code = 0;
    int surface_stations = 0, upper_stations = 0, precipitation_stations = 0;
    int comment_records = 0;
    float dx_m = 0, origin_x_m = 0, origin_y_m = 0;
    std::string timezone;
};
struct Calmet21Field {
    std::string label;
    Calmet21Time begin, end;
    bool integer = false;
    std::vector<float> real_values;
    std::vector<std::int32_t> integer_values;
};
// Static header fields of the original CALMET.DAT 2.1 OUTHD section, written
// before the first hourly field (CALMET calmet.for L12482-12536): ZFACE
// (nz+1 reals), station coordinates, then the per-cell grids Z0, ILANDU
// (written as INTEGER by WRTI2D), ELEV, XLAI and NEARS (INTEGER). P7G decodes
// them because the dry-deposition and terrain/shear paths need per-cell
// roughness, land use and leaf area index.
struct Calmet21Static {
    bool present = false;
    std::vector<float> cell_face_m;              // ZFACE, nz+1
    std::vector<float> roughness_m;              // Z0, nx*ny
    std::vector<std::int32_t> land_use;          // ILANDU, nx*ny integers
    std::vector<float> elevation_m;              // ELEV, nx*ny
    std::vector<float> leaf_area_index;          // XLAI, nx*ny
    std::vector<std::int32_t> nearest_station;   // NEARS, nx*ny integers (optional)
    std::size_t decoded_records = 0;
};

struct Calmet21Summary {
    Calmet21Header header;
    std::size_t intervals = 0, hourly_fields = 0, metadata_records = 0;
    Calmet21Time first_begin, final_end;
    Calmet21Static statics;
};

// Original CALMET 6.5.0 CALMET.DAT 2.1, IRTYPE=1, IWFCOD=1.
// Reads all 3D wind/temp and gridded 2D fields through a typed observer.
// Record layout from OUTHD, OUTHR, WRTR2D, WRTI2D. No claims of wind parity.
class Calmet21Reader {
public:
    using Observer = std::function<void(const Calmet21Field&)>;
    static Calmet21Summary read(const std::string& path,
                                const Observer& observer = {},
                                bool frozen_hefei_2022 = false);
};
} // namespace cteas::puff
