#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <map>
#include <string>
#include <vector>

namespace cteas::puff {

// P7E: CONC.DAT record framing for the CALPUFF output dataset.
//
// Every record is a sequential-unformatted Fortran record with 4-byte markers,
// exactly as the vendor writers do it (calpuff.for WRTI1D L64706-64739,
// WRTR1D L64741-64774, WRTR2D L64776-64826); that framing is byte-verified
// against those unmodified vendor routines by CTest.
//
// The record *contents* follow the locked case's original CONC.DAT as measured
// from project/cases/hefei5km_2022_reference_case_20261011/run/puff/puff.con:
//   version record      96 bytes  'CONC.DAT' + data version + model version
//   comment count        4 bytes  number of following comment records
//   comment record     132 bytes  one input-file line
//   period record       32 bytes  (year, julian, hour, seconds) x2, no label
//   grid descriptor     32 bytes  (nrec, group index, 'TOTAL' 16 chars, XORIGKM, YORIGKM)
//   species field       8 + 7 + 4*nx*ny bytes  label + right-justified species index + values
// The values are this module's own; only the structure is comparable with the
// frozen artifact (the original values need the full puff model).
//
// The remaining WROUT1 header records (model run info, source/receptor group
// tables, chemistry labels) are NOT reconstructed, so the original
// post-processing toolchain cannot read these files yet.

struct ConcRecord {
    std::string label;                 // exactly 8 characters
    int begin_date = 0;                // YYYYJJJHH
    int begin_seconds = 0;             // SSSS
    int end_date = 0;
    int end_seconds = 0;
    std::vector<float> values;
};

// Structure inventory of a CONC.DAT-like file: what a comparison against the
// frozen original artifact can legitimately check today.
struct ConcFileSummary {
    std::size_t records = 0;
    std::size_t period_records = 0;      // 32-byte (year, julian, hour, seconds) x2
    std::size_t grid_records = 0;        // 32-byte grid descriptor
    std::size_t species_field_records = 0; // label + 7-byte index + values
    std::vector<std::pair<std::string, std::size_t>> species_field_counts; // label -> count
    std::vector<std::size_t> species_field_sizes;
    std::size_t bytes = 0;
    std::vector<std::size_t> record_sizes;               // per record, in order
    std::vector<std::pair<std::string, std::size_t>> label_counts; // first appearance order
    std::size_t framed_records = 0;                      // label + four date words
    std::size_t unframed_records = 0;
    std::vector<std::size_t> framed_sizes;               // sizes of the framed records
    int first_begin_date = 0;
    int last_end_date = 0;
};

// Original CALPUFF OUTPUT L57913 is a SOURCE descriptor (not a grid).
// KTYPE/KSOURCE/CSRCNAM/XMAPKM/YMAPKM; TOTAL is 0/1/TOTAL/origin.
struct ConcSourceDescriptor {
    int source_type=0;
    int source_index=1;
    std::string source_name="TOTAL";
    double x_map_km=0.0;
    double y_map_km=0.0;
};
[[nodiscard]] ConcSourceDescriptor original_total_source_descriptor(
    float origin_x_m,float origin_y_m);

// Legacy TOTAL-only descriptor naming for older tests/callers.
struct ConcPeriod {
    int begin_year = 0, begin_julian = 0, begin_hour = 0, begin_seconds = 0;
    int end_year = 0, end_julian = 0, end_hour = 0, end_seconds = 0;
};

struct ConcGridDescriptor {
    int discrete_receptors = 0;
    int group_index = 1;             // original WROUT1 TOTAL receptor group (1-based)
    std::string group_name = "TOTAL";
    double x_origin_km = 0.0;
    double y_origin_km = 0.0;
};

// Rebuild original WROUT1 grid header from the CALMET.DAT ORIGIN IN METRES.
// The vendor stores origin in REAL*4 metres and evaluates:
//    XORIGKM = XMET0 * REAL4(0.001)
// before writing the REAL*4 kilometres. Parsing the 3-decimal puff.inp
// XORIGKM/YORIGKM and merely casting to float gives a different Y origin
// (3531.26904296875 rather than original 3531.269287109375 in Hefei).
[[nodiscard]] ConcGridDescriptor original_met_grid_descriptor(
    float origin_x_m, float origin_y_m, int discrete_receptors = 0);


// Four original WROUT1 metadata records after the two numeric run headers:
// 3*CHARACTER*80 run titles (240B), CHAR*8 + I7 species (15B),
// CHARACTER*16 concentration units (16B), I4+CHARACTER*16 source (20B).
// This does NOT infer or write the preceding 300/52-byte numeric records
// or reconstruct the 3218 embedded input/control echo records.
// Original CALPUFF 7.2.1 WROUT1 L57177-L57183 (300-byte record).
// Input data is typed, independently assembled by the caller, and never
// accepted from a frozen/output binary. The arrays reflect literal vendor
// field order: timing/grid=[IRLG,IAVG,NSECDT,NX,NY]; options=[NSSTA1,
// IBCOMP,IECOMP,JBCOMP,JECOMP,IBSAMP,JBSAMP,IESAMP,JESAMP,MESHDN,
// NSRCTYPE,MSOURCE,NREC,NRGRP,NCTREC,LSAMP,NSPOUT,LCOMPRS,I2DMET,IUTMZN];
// projection=[FEAST,FNORTH,RNLAT0,RELON0,XLAT1,XLAT2].
// Source-derived CALPUFF WROUT1 comment stream (L57135-57174):
// 2 vendor provenance lines; original puff.inp raw text lines;
// 3 separator lines + MET.DAT's own version record; then MET.DAT's
// 132-byte original embedded header comments. No output oracle input.
[[nodiscard]] std::vector<std::string> original_wrout1_embedded_comments(
    const std::string& active_puff_control,
    const std::string& calmet_dat_path);

struct OriginalWrout1GeneralHeader {
    std::string model="CALPUFF";
    std::string model_version="7.2.1";
    std::string model_level="150618";
    std::array<std::int32_t,4> start{}; // IBYR,IBJUL,IBHR,IBSEC
    std::string timezone;
    std::array<std::int32_t,5> timing_grid{};
    std::array<float,2> spacing_km{};
    std::int32_t original_one=1;
    std::array<float,2> met_origins_km{};
    std::array<std::int32_t,20> options{};
    std::array<float,6> projection{};
    std::string pmap, utmhem, datum, datum_epoch;
    std::array<std::string,4> latlon_labels{}; // CLAT0,CLON0,CLAT1,CLAT2
};

struct OriginalWrout1Identity {
    std::array<std::string,3> run_titles{};
    std::string species_name="H-3";
    int species_index=1;
    std::string concentration_units="Bq/m3";
    int source_identifier=1;
    std::string source_name="HTO_STACK";
};

class ConcFileWriter {
public:
    // `data_version` and `model_version` are written into the version record
    // (16 and 64 characters, matching the vendor record size of 96 bytes).
    ConcFileWriter(const std::string& path, std::string data_version, std::string model_version,
                   std::vector<std::string> comments);
    ~ConcFileWriter();

    ConcFileWriter(const ConcFileWriter&) = delete;
    ConcFileWriter& operator=(const ConcFileWriter&) = delete;

    void write_record(const ConcRecord& record);
    // CONC.DAT v2.2 forms measured from the frozen artifact.
    void write_period_record(const ConcPeriod& period);
    void write_grid_descriptor(const ConcGridDescriptor& descriptor);
    // Original OUTPUT L57913: int32/int32/CHARACTER*16/REAL4/REAL4.
    void write_source_descriptor(const ConcSourceDescriptor& descriptor);
    // Emit all four independently constructed selected-case metadata records.
    void write_original_wrout1_identity(const OriginalWrout1Identity& identity);
    // Original WROUT1 L57184: 13 Fortran INTEGER*4 source-type counters
    // in ordinal order, present immediately after 300-byte run metadata.
    // The native caller supplies the actual selected-case counts.
    void write_original_wrout1_source_type_counts(
        const std::array<std::int32_t,13>& source_count);
    void write_original_wrout1_general_header(
        const OriginalWrout1GeneralHeader& header);
    void write_species_field(const std::string& label, int species_index, int nx, int ny,
                             const std::vector<float>& values);
    void close();
    [[nodiscard]] std::size_t records_written() const noexcept { return records_written_; }

private:
    struct Impl;
    Impl* impl_ = nullptr;
    std::size_t records_written_ = 0;
};

// Fail-closed record validation: label length, finite values, and date/second
// ranges consistent with the vendor encoding (YYYYJJJHH with hour 0-24 and
// seconds 0-3600, years 1900-2100).
void validate_conc_record(const ConcRecord& record);
void validate_conc_field(const ConcRecord& record, int nx, int ny);

[[nodiscard]] ConcFileSummary summarize_conc_file(const std::string& path);

// Reads back the records this module writes (label + four date words + values).
// Throws for truncated or inconsistent framing.
[[nodiscard]] std::vector<ConcRecord> read_conc_records(const std::string& path);

struct ConcSpeciesField {
    std::string label;
    int species_index = 0;
    std::vector<float> values;
};

// CONC.DAT readers. The species-field reader validates the value count against
// the expected grid (fail closed on a dimension, species-count or time-label
// mismatch).
[[nodiscard]] std::vector<ConcPeriod> read_conc_periods(const std::string& path);
[[nodiscard]] std::vector<ConcSpeciesField> read_conc_species_fields(const std::string& path, int nx,
                                                                    int ny);

} // namespace cteas::puff
