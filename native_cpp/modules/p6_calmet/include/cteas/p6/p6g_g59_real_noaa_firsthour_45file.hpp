#pragma once
// S4-R1c8k: authentic NOAA source-native first-hour CALMET.DAT
// 2.1 test-only P6F file. All 45 hourly values are produced by
// previously source-audited native physics G57 (43 REAL) + G58 (2 INT).
// The header/statics come from genuine GEO.DAT / met.inp / station
// identity via the existing frozen G18C6/P6F serializer.
// This remains detached from the live 17-stage G14 hourly transaction,
// so the full six-hour P6 production and P7 are NOT admitted.
#include "cteas/p6/p6g_g58_real_noaa_ipgt_irh.hpp"
#include "cteas/p6/p6g_g18c6_selected_p6f_dataset.hpp"
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>
namespace cteas::calmet::p6g {
struct G59RealNoaaOneHourFile {
    std::chrono::sys_seconds end{};
    std::vector<std::uint8_t> calmet_dat21;
    std::size_t native_hourly_fields=0,native_real=0,native_integer=0;
    bool test_only_firsthour_legal_file=false;
    bool full_sixhour_causal_g14_ready=false;
    bool p7_ready=false;
};
inline G59RealNoaaOneHourFile g59_native_noaa_firsthour_45file(
    const G19SourceFilePaths& paths,bool explicitly_test_only) {
    if(!explicitly_test_only)
        throw std::invalid_argument(
            "G59 genuine one-hour P6F file never authorizes full G14/P7");
    const auto source=g41_load_selected_noow_water_first_hour_source(
        paths,true);
    const auto g57=g57_noaa_real_43_output_fields(paths,true);
    const auto g58=g58_source_noaa_p6f_ipgt_irh(paths,true);
    auto scheduler=source.source.make_scheduler();
    const auto frame=scheduler.preview_next_hour();
    const auto& geo=source.source.grid;
    const auto n=static_cast<std::size_t>(geo.nx)*
                 static_cast<std::size_t>(geo.ny);
    if(frame.hour_index!=0||scheduler.completed_hours()!=0||
       frame.input.end!=g57.end||frame.input.end!=g58.end||
       !g57.source_firsthour_43real_only||
       !g58.source_only_two_integer_fields||
       g57.g26_45field_ready||g57.six_hour_causal_ready||
       g58.p6f_45field_file_ready||g58.g14_six_hour_causal_ready||
       g57.source_land!=6907||g57.source_water!=63||
       g58.original_land!=6907||g58.original_water!=63||
       g57.fields.size()!=43||g58.ipgt.size()!=n||
       g58.irh.size()!=n||n!=6970)
        throw std::invalid_argument("G59 source physical hour not independently owned");
    G18C5SelectedHourFields fields;
    fields.end=frame.input.end;
    for(const auto& s:source.source.stations.surface)
        fields.station_ids.push_back(s.id);
    for(const auto& p:g57.fields) {
        if(p.first.size()!=8||p.second.size()!=n||
           !fields.real.emplace(p.first,p.second).second)
            throw std::invalid_argument("G59 duplicate/missing REAL P6F field");
    }
    fields.integer.emplace("IPGT    ",g58.ipgt);
    fields.integer.emplace("IRH     ",g58.irh);
    if(fields.real.size()!=43||fields.integer.size()!=2)
        throw std::logic_error("G59 source 43+2 P6F inventory incomplete");
    // G18C6 is the preexisting original-backed P6F writer with
    // explicit source controls, original SETCOM NEARS and original
    // GEO static field checks. Never copy the original output file.
    const auto nears=source_setcom_nears(
        source.source.grid,source.source.stations);
    const auto candidate=g18c6_selected_one_hour_dataset(
        frame,fields,nears,source.source.original_metinp,true,
        false,true);
    if(candidate.hourly.size()!=45||
       candidate.header.irlg!=1||
       candidate.header.nssta!=2||
       candidate.header.nusta!=1||
       candidate.header.npsta!=0||
       candidate.header.nx!=82||candidate.header.ny!=85||
       candidate.header.nz!=9)
        throw std::logic_error("G59 P6F output source header/clock detached");
    auto bytes=cteas::p6f::serialize_calmet_dat21(candidate);
    if(bytes.empty())
        throw std::logic_error("G59 empty source P6F CALMET.DAT");
    const auto parsed=cteas::p6f::parse_calmet_dat21(bytes);
    if(parsed.hourly.size()!=45||parsed.header.irlg!=1||
       parsed.header.nssta!=2||parsed.header.nusta!=1||
       parsed.header.npsta!=0)
        throw std::logic_error("G59 frozen serializer round-trip failed");
    return {frame.input.end,std::move(bytes),45,43,2,true,false,false};
}
} // namespace cteas::calmet::p6g
