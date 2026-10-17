#include "cteas/puff/hourly_conc.hpp"

#include <cmath>
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <utility>

namespace cteas::puff {
namespace {

bool leap(int year) {
    return year % 4 == 0 && (year % 100 != 0 || year % 400 == 0);
}

std::int64_t timestamp_seconds(int year, int julian, int hour, int seconds) {
    if (year < 1900 || year > 2100 || julian < 1 ||
        julian > (leap(year) ? 366 : 365) ||
        hour < 0 || hour > 23 || seconds != 0) {
        throw std::invalid_argument("P7E hourly series: invalid year/day/hour boundary");
    }
    std::int64_t days = 0;
    for (int y = 1900; y < year; ++y) days += leap(y) ? 366 : 365;
    days += julian - 1;
    return (days * 24 + hour) * 3600;
}

} // namespace

HourlyConcSeriesWriter::HourlyConcSeriesWriter(
    ConcFileWriter& output, ConcSourceDescriptor source, int nx, int ny,
    std::string species, int species_index)
    : output_(output), source_(std::move(source)), nx_(nx), ny_(ny),
      species_(std::move(species)), species_index_(species_index),
      cell_count_(0) {
    if (nx_ <= 0 || ny_ <= 0 ||
        static_cast<std::size_t>(nx_) >
            std::numeric_limits<std::size_t>::max() / static_cast<std::size_t>(ny_)) {
        throw std::invalid_argument("P7E hourly series: invalid grid dimensions");
    }
    cell_count_ = static_cast<std::size_t>(nx_) * static_cast<std::size_t>(ny_);
    if (species_.empty() || species_.size() > 8 ||
        species_index_ < 1 || species_index_ > 9999999 ||
        source_.source_type < 0 || source_.source_type > 8 ||
        source_.source_index < 1 ||
        source_.source_name.empty() || source_.source_name.size() > 16 ||
        !std::isfinite(source_.x_map_km) || !std::isfinite(source_.y_map_km)) {
        throw std::invalid_argument("P7E hourly series: invalid species/grid metadata");
    }
}

HourlyConcSeriesWriter::HourlyConcSeriesWriter(
    ConcFileWriter& output, ConcGridDescriptor grid, int nx, int ny,
    std::string species, int species_index)
    :HourlyConcSeriesWriter(output,
        ConcSourceDescriptor{grid.discrete_receptors,grid.group_index,
         grid.group_name,grid.x_origin_km,grid.y_origin_km},
        nx,ny,std::move(species),species_index) {}

void HourlyConcSeriesWriter::write_hour(
    const ConcPeriod& period, const std::vector<float>& values) {
    // Fail closed BEFORE writing the first of three sequential records.
    const auto start = timestamp_seconds(
        period.begin_year, period.begin_julian, period.begin_hour, period.begin_seconds);
    const auto finish = timestamp_seconds(
        period.end_year, period.end_julian, period.end_hour, period.end_seconds);
    if (finish - start != 3600 ||
        (hours_written_ > 0 && start != next_start_second_)) {
        throw std::invalid_argument("P7E hourly series: gap, overlap or non-hourly period");
    }
    if (values.size() != cell_count_) {
        throw std::invalid_argument("P7E hourly series: wrong receptor field cell count");
    }
    for (float value : values) {
        if (!std::isfinite(value)) {
            throw std::invalid_argument("P7E hourly series: non-finite concentration");
        }
    }
    output_.write_period_record(period);
    output_.write_source_descriptor(source_);
    output_.write_species_field(species_, species_index_, nx_, ny_, values);
    next_start_second_ = finish;
    ++hours_written_;
}

} // namespace cteas::puff
