#pragma once
// ---------------------------------------------------------------------------
// CTEAS P6F -- C++ writer for a legal CALMET.DAT 2.1 file.
//
// This module turns explicitly supplied field arrays (three-dimensional wind
// components per level, the 3-D temperature field, the surface/upper-air/
// precipitation station tables, the static grid records and the run control
// block with its time labels) into the exact binary file the original CALMET
// 6.5.0 writes, so that the unmodified CALPUFF can read it.
//
// Layout facts are taken from the unmodified original sources
//
//   engine/vendor/src/CALMET_v6.5.0_L150223/calmet.for
//       OUTHD          L12448-L12537  (declaration, comments, controls, statics)
//       OUTHR          L13067-L13237  (hourly field order and labels)
//       WRTR1D         L36789-L36816  (one-dimensional real record)
//       WRTR2D         L36829-L36881  (two-dimensional real record)
//       WRTI2D         L36734-L36788  (two-dimensional integer record)
//   engine/vendor/src/CALMET_v6.5.0_L150223/map.met L5-L7
//       character*4 utmhem / character*8 datum,pmap / character*12 daten
//
// and were verified byte-for-byte against the frozen real 2022 reference case
//
//   project/cases/hefei5km_2022_reference_case_20261011/run/met/met.dat
//   64,762,556 B, sha256
//   b1823cda92280888d70b00961ab39486036a3086e18637fff21efb4f4b237d30
//   143 one-hour intervals, 7,562 Fortran records, NX=NY=50, NZ=9,
//   IRTYPE=1, IWFCOD=1, LCALGRD=T, NSSTA=1, NUSTA=1, NPSTA=0, 1,114 comments.
//
// Record framing is Fortran sequential unformatted, little endian:
//   int32 byte count + payload + the same int32 byte count.
//
// Record sequence:
//   #1              file declaration, 96 B =
//                   char*16 dataset | char*16 version | char*64 model
//   #2              int32 NCOM (number of comment records)
//   #3 .. #NCOM+2   NCOM comment records of 132 B each
//   #NCOM+3         run controls, 176 B, in the OUTHD order documented below
//   #NCOM+4         ZFACE                       (NZ+1 reals, metres)
//   then            XSSTA, YSSTA                (NSSTA reals each, metres)
//                   XUSTA, YUSTA                (NUSTA reals each, metres)
//                   XPSTA, YPSTA                (NPSTA reals each, metres)
//                   Z0, ILANDU, ELEV, XLAI      (NX*NY words each)
//                   NEARS                       (NX*NY ints, only if NSSTA>=1)
//   then per hour   U-LEV1 V-LEV1 [WFACE1] U-LEV2 ... U-LEVn V-LEVn [WFACEn]
//                   [T-LEV1 .. T-LEVn]          (only if LCALGRD)
//                   IPGT USTAR ZI EL WSTAR [RMM] TEMPK RHO QSW IRH [IPCODE]
//                   (the bracketed fields appear only for NPSTA != 0)
//
// Every data record is 24 B of header -- char*8 label, int32 packed begin date
// YYYYJJJHH, int32 begin seconds, int32 packed end date, int32 end seconds --
// followed by NX*NY four-byte words: 24 + 4*NX*NY bytes. The static records
// carry the same header shape with four zero clock words.
//
// Explicit semantics enforced here (all violations fail closed):
//   * time    packed YYYYJJJHH plus an explicit seconds word; each hourly
//             interval is exactly 3600 s, the original writes the end clock as
//             the same packed hour with seconds advanced to 3600, and the
//             interval sequence is contiguous; AXTZ is the 8-character zone
//             label (the frozen case is "UTC+0000"); the controls record also
//             carries the declared run begin/end clock words.
//   * units   see field_specs(); the file stores SI throughout.
//   * masks   the field set is fully determined by IRTYPE/LCALGRD/NPSTA and the
//             station counts: a field that the original would not write (for
//             example RMM/IPCODE with NPSTA=0) is rejected instead of being
//             renamed or dropped, and a missing field of a declared hour is
//             rejected instead of being filled.
//   * missing the original sentinel is XMISS = 9999. for real fields and 9999
//             for integer fields; it is a legal value and is preserved
//             bit-exactly. Values the original never writes (ZICONV, DPTT, QH)
//             have no file representation and are rejected by label.
//
// Byte identity with the frozen real case is the writer's ground truth: see
// the `roundtrip` command of the CLI and the CTest set of this module.
// ---------------------------------------------------------------------------
#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace cteas::p6f {

// ---------------------------------------------------------------- constants
inline constexpr std::size_t record_marker_bytes = 4;
inline constexpr std::size_t declaration_bytes = 96;
inline constexpr std::size_t comment_bytes = 132;
inline constexpr std::size_t controls_bytes = 176;
inline constexpr std::size_t controls_prefix_bytes = 116;
inline constexpr std::size_t controls_tail_bytes = 60;
inline constexpr std::size_t field_header_bytes = 24;
inline constexpr std::uint32_t max_comment_records = 10000;
// XMISS of CALMET 6.5.0: the sentinel the original leaves in unwritten fields.
inline constexpr float missing_real = 9999.f;
inline constexpr std::int32_t missing_integer = 9999;
inline bool is_missing(float v) { return v == missing_real; }
inline bool is_missing(std::int32_t v) { return v == missing_integer; }

// -------------------------------------------------------------------- time
// Packed original date/time word YYYYJJJHH (year, day of year, hour).
struct Calmet21Time {
    int year = 0;
    int julian_day = 0;
    int hour = 0;
    int seconds = 0;
};
inline bool is_leap_year(int year) {
    return year % 4 == 0 && (year % 100 != 0 || year % 400 == 0);
}
inline int days_in_year(int year) { return is_leap_year(year) ? 366 : 365; }
// Days since 1970-01-01 for a proleptic Gregorian calendar date.
std::int64_t days_from_civil(int year, unsigned month, unsigned day);
// Inverse of days_from_civil (used to build explicit time labels).
Calmet21Time civil_from_days(std::int64_t days);
// Decomposed civil date/clock of an absolute instant, for reporting.
struct Calmet21Calendar {
    int year = 0, month = 0, day = 0, hour = 0, minute = 0, second = 0;
};
Calmet21Calendar calendar_from_instant(std::int64_t instant);
// "YYYY-MM-DDTHH:MM:SSZ" of an absolute instant.
std::string iso8601_utc(std::int64_t instant);
// YYYYJJJHH of the original; requires 0<=hour<=23.
std::int32_t pack_time(const Calmet21Time& time);
Calmet21Time unpack_time(std::int32_t packed, int seconds);
// Absolute UTC instant of the explicit time label.
std::int64_t instant_seconds(const Calmet21Time& time);
Calmet21Time instant_to_time(std::int64_t instant);
Calmet21Time next_hour(Calmet21Time time);

// --------------------------------------------------------------- structures
// Bytes 116..175 of the controls record: the OUTHD map/projection block.
// The original declaration order and widths are
//   pmap char*8 | datum char*8 | daten char*12 | feast real | fnorth real |
//   utmhem char*4 | iutmzn integer | rnlat0 real | relon0 real |
//   xlat1 real | xlat2 real                                (60 bytes total)
// The frozen case carries pmap="UTM     ", datum="WGS-84  ",
// daten="02-21-2003  ", feast=fnorth=0, utmhem="N   ", iutmzn=50 and
// rnlat0=relon0=xlat1=xlat2=0.
struct Calmet21Projection {
    std::string pmap;   // character*8
    std::string datum;  // character*8
    std::string daten;  // character*12
    float feast = 0.f;
    float fnorth = 0.f;
    std::string utmhem;  // character*4
    std::int32_t iutmzn = 0;
    float rnlat0 = 0.f;
    float relon0 = 0.f;
    float xlat1 = 0.f;
    float xlat2 = 0.f;
};

// The declaration record plus the run control block (record #NCOM+3).
struct Calmet21Header {
    std::string dataset = "CALMET.DAT";  // char*16
    std::string version = "2.1";         // char*16
    std::string model = "No-Obs file structure with embedded control file";
    std::vector<std::string> comments;  // NCOM records of at most 132 bytes

    // IBYRN..IESECN: the run clock words declared by the original controls.
    // They are explicit calendar dates (year, month, day, hour) plus a seconds
    // word holding the offset inside that hour (0..3600, the original's
    // sub-hourly step support), not the packed YYYYJJJHH of the field records
    // and not a clock second. The frozen case starts and ends on the hour, so
    // its seconds words are zero.
    int begin_year = 0, begin_month = 0, begin_day = 0, begin_hour = 0, begin_second = 0;
    int end_year = 0, end_month = 0, end_day = 0, end_hour = 0, end_second = 0;

    std::string timezone = "UTC+0000";  // AXTZ, exactly 8 characters
    std::int32_t irlg = 0;              // number of hourly intervals written
    std::int32_t irtype = 1;            // 1 = winds + meteorological fields
    int nx = 0, ny = 0, nz = 0;
    float dgrid_m = 0.f, xorigin_m = 0.f, yorigin_m = 0.f;
    std::int32_t iwfcod = 1;  // 1 = write u, v and w
    std::int32_t nssta = 0, nusta = 0, npsta = 0;  // station counts
    std::int32_t nowsta = 0;                       // overwater stations
    std::int32_t nlu = 0;                          // land-use categories
    std::int32_t iwat1 = 50, iwat2 = 55;           // water land-use range
    bool lcalgrd = true;                           // write W and T fields
    Calmet21Projection projection;
};

// NCOM+4 .. the static records, in OUTHD order.
struct Calmet21Statics {
    std::vector<float> zface_m;              // NZ+1 cell faces, metres
    std::vector<float> surface_x_m, surface_y_m;  // NSSTA
    std::vector<float> upper_x_m, upper_y_m;      // NUSTA
    std::vector<float> precip_x_m, precip_y_m;    // NPSTA
    std::vector<float> z0_m;                 // NX*NY roughness length, metres
    std::vector<std::int32_t> ilandu;        // NX*NY land-use category
    std::vector<float> elev_m;               // NX*NY terrain height, metres
    std::vector<float> xlai;                 // NX*NY leaf area index, m2/m2
    std::vector<std::int32_t> nears;         // NX*NY nearest surface station
};

// One NX*NY field record.
struct Calmet21Field {
    std::string label;  // exactly the label written by the original, e.g. "U-LEV  1"
    Calmet21Time begin, end;
    bool integer = false;
    std::vector<float> real_values;         // used when integer == false
    std::vector<std::int32_t> integer_values;  // used when integer == true
};

struct Calmet21File {
    Calmet21Header header;
    Calmet21Statics statics;
    std::vector<Calmet21Field> hourly;  // intervals * fields_per_interval records
};

// ------------------------------------------------------------------ layout
// A label is an integer field only for IPGT and IRH (OUTHR uses WRTI2D there).
bool is_integer_label(const std::string& label);
// The exact OUTHR label sequence for the selected output mode.
std::vector<std::string> hourly_labels(int nz, int irtype, bool lcalgrd,
                                       int npsta);
// Derived record-group shape; both are functions of the header and of the
// number of hourly records, so they can never drift out of sync.
std::size_t fields_per_interval(const Calmet21Header& header);
std::size_t interval_count(const Calmet21File& file);
// Declared unit/ownership/mask metadata for every field of the selected mode.
struct Calmet21FieldSpec {
    std::string label;
    std::string unit;          // SI unit of the stored value
    bool integer = false;      // stored as int32 rather than real32
    std::string written_when;  // the original condition that puts it in the file
    std::string source;        // who must supply the explicit values
};
std::vector<Calmet21FieldSpec> hourly_field_specs(int nz, int irtype,
                                                  bool lcalgrd, int npsta);
std::vector<Calmet21FieldSpec> static_field_specs(int nx, int ny, int nz,
                                                  int nssta, int nusta,
                                                  int npsta);
// Labels with no CALMET.DAT representation at all; the writer rejects them.
// A label that is not part of the selected layout is also rejected.
inline std::vector<std::string> internal_only_labels() {
    return {"ZICONV", "DPTT", "QH", "USTAROLD", "T2", "IPGT2"};
}

// ---------------------------------------------------------------------- io
// Every failure is std::invalid_argument with the "P6F CALMET.DAT 2.1 " prefix.
// Validate the explicit dataset and serialise it into a byte image.
std::vector<std::uint8_t> serialize_calmet_dat21(const Calmet21File& file);
// Validate the dataset without serialising it.
void validate_calmet_dat21(const Calmet21File& file);
// Parse and validate a CALMET.DAT 2.1 byte image; strings are kept verbatim
// (with their original padding) so that parse|serialize is the identity.
Calmet21File parse_calmet_dat21(const std::vector<std::uint8_t>& bytes);
Calmet21File read_calmet_dat21(const std::string& path);
// The native P6E "emit-realcase --hours 1" transport has one hour's
// actual 45 weather fields, but its copied run-control calendar can still
// describe a longer source window. Normalize ONLY the control calendar
// in-memory from the one-hour field clocks before applying all of the same
// strict CALMET.DAT structural and numerical invariants. Never use this
// loader for independent reference/oracle validation.
Calmet21File read_calmet_dat21_native_one_hour(const std::string& path);
void write_calmet_dat21(const std::string& path, const Calmet21File& file);

// Per-field inventory of a dataset, used by the file checker: the denominator
// is the number of stored cells, `missing` counts the XMISS sentinel and
// `defined` the cells that carry a real observation. minimum/maximum/mean are
// computed over the defined cells only and are NaN when there are none.
struct Calmet21FieldStats {
    std::string label;
    std::string unit;
    bool integer = false;
    std::size_t records = 0;  // number of file records carrying this label
    std::size_t values = 0;   // records * NX * NY
    std::size_t defined = 0;  // values that are not the XMISS sentinel
    std::size_t missing = 0;  // values equal to the sentinel
    double minimum = 0.0, maximum = 0.0, mean = 0.0;
};
std::vector<Calmet21FieldStats> field_inventory(const Calmet21File& file);

}  // namespace cteas::p6f
