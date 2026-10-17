#pragma once

#include "cteas/puff/conc_file.hpp"

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace cteas::puff {

// Native original OUTPUT hourly DATA; WROUT1 constructs only the header.
// Each accepted hour appends: period (32), SOURCE descriptor (32), H-3 field
// (15 + nx*ny*4). The caller MUST calculate the concentrations independently;
// this class does not read oracle values or reconstruct the vendor file preamble.
// It cannot produce a standalone CALPUFF-compatible puff.con until original
// WROUT1 headers and source tables have been implemented separately.
class HourlyConcSeriesWriter {
public:
    HourlyConcSeriesWriter(ConcFileWriter& output, ConcSourceDescriptor source,
                           int nx, int ny, std::string species = "H-3",
                           int species_index = 1);
    // Legacy TOTAL-only overload.
    HourlyConcSeriesWriter(ConcFileWriter& output, ConcGridDescriptor grid,
                           int nx, int ny, std::string species = "H-3",
                           int species_index = 1);

    // All 3 record bodies are validated BEFORE any record is written.
    // Requires UTC/selected-case clock hours, 3600 s duration and no gaps.
    // Do not reuse output after an underlying I/O exception: the three
    // sequential records are not a filesystem transaction.
    void write_hour(const ConcPeriod& period, const std::vector<float>& values);
    [[nodiscard]] std::size_t hours_written() const noexcept { return hours_written_; }

private:
    ConcFileWriter& output_;
    ConcSourceDescriptor source_;
    int nx_;
    int ny_;
    std::string species_;
    int species_index_;
    std::size_t cell_count_;
    std::size_t hours_written_ = 0;
    std::int64_t next_start_second_ = -1;
};

} // namespace cteas::puff
