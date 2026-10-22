#pragma once
// S4-R1c8k: integrate genuinely source-native 43 REAL4 + 2 INTEGER4
// values with the EXISTING CALMET.DAT 2.1 writer and source GEO/clock.
// One verified physical hour only. Never promote G14 six-hour, G26,
// P7 or an unsupported original branch to production on this evidence.
#include "cteas/p6/p6g_g58_real_noaa_ipgt_irh.hpp"
#include "cteas/p6/p6g_g18c6_selected_p6f_dataset.hpp"
#include <cstddef>
#include <cstdint>
#include <stdexcept>
#include <utility>

namespace cteas::calmet::p6g {

struct G59FirstHourFileCandidate {
    cteas::p6f::Calmet21File dataset;
    bool firsthour_source_native_45_record_dataset=false;
    bool g14_six_hour_causal=false;
    bool g26_production=false;
    bool p7_accepted=false;
};

inline G59FirstHourFileCandidate g59_source_noaa_firsthour_dataset(
    const G19SourceFilePaths& paths, bool explicitly_firsthour_only) {
    if (!explicitly_firsthour_only)
        throw std::invalid_argument("G59 requires explicit source-only firsthour");
    // Both original-independent kernels have separately passed the genuine
    // NOAA first-hour full-domain physical comparison with original CALMET.
    const auto physical = g57_noaa_real_43_output_fields(paths, true);
    const auto integer = g58_source_noaa_p6f_ipgt_irh(paths, true);
    const auto original_source = g41_load_selected_noow_water_first_hour_source(
        paths, true);
    const auto scheduler = original_source.source.make_scheduler();
    const auto frame = scheduler.preview_next_hour();
    const std::size_t n = static_cast<std::size_t>(frame.grid.nx) *
                          static_cast<std::size_t>(frame.grid.ny);
    if (!physical.source_firsthour_43real_only ||
        !integer.source_only_two_integer_fields ||
        physical.g26_45field_ready || physical.six_hour_causal_ready ||
        integer.p6f_45field_file_ready || integer.g14_six_hour_causal_ready ||
        physical.end != integer.end || physical.end != frame.input.end ||
        frame.hour_index != 0 || scheduler.completed_hours() != 0 ||
        frame.grid.nx != 82 || frame.grid.ny != 85 || n != 6970 ||
        frame.stations.surface.size() != 2 ||
        frame.stations.upper.size() != 1 ||
        physical.source_land != 6907 || physical.source_water != 63 ||
        integer.original_land != 6907 || integer.original_water != 63 ||
        physical.fields.size() != 43 || integer.ipgt.size() != n ||
        integer.irh.size() != n)
        throw std::invalid_argument("G59 source firsthour physical state incomplete");

    G18C5SelectedHourFields joined;
    joined.end = frame.input.end;
    for (const auto& station : frame.stations.surface) {
        if (station.id <= 0)
            throw std::invalid_argument("G59 invalid original source SS");
        joined.station_ids.push_back(station.id);
    }
    for (const auto& field : physical.fields)
        if (field.first.size() != 8 || field.second.size() != n ||
            !joined.real.emplace(field.first, field.second).second)
            throw std::invalid_argument("G59 duplicate or missing REAL4 record");
    joined.integer.emplace("IPGT    ", integer.ipgt);
    joined.integer.emplace("IRH     ", integer.irh);
    if (joined.real.size() != 43 || joined.integer.size() != 2)
        throw std::logic_error("G59 not exactly 45 native fields");

    // Original SETCOM-derived nearest-station geometry is recomputed only
    // from GEO and actual stations. No original MET.DAT physics is supplied.
    const auto nears = source_setcom_nears(frame.grid, frame.stations);
    auto dataset = g18c6_selected_one_hour_dataset(
        frame, joined, nears, original_source.source.original_metinp,
        true, false, true);
    const auto labels = cteas::p6f::hourly_labels(9, 1, true, 0);
    if (dataset.hourly.size() != 45 || labels.size() != 45 ||
        dataset.header.irlg != 1 || dataset.header.nssta != 2 ||
        dataset.header.nusta != 1 || dataset.header.npsta != 0 ||
        dataset.header.nx != 82 || dataset.header.ny != 85 ||
        dataset.header.nz != 9 || dataset.statics.nears.size() != n)
        throw std::logic_error("G59 legal P6F one-hour structure incomplete");
    for (std::size_t k = 0; k < labels.size(); ++k)
        if (dataset.hourly[k].label != labels[k] ||
            dataset.hourly[k].integer != cteas::p6f::is_integer_label(labels[k]))
            throw std::logic_error("G59 original OUTHR field type/order changed");
    cteas::p6f::validate_calmet_dat21(dataset);
    G59FirstHourFileCandidate result;
    result.dataset = std::move(dataset);
    result.firsthour_source_native_45_record_dataset = true;
    return result;
}

} // namespace cteas::calmet::p6g
