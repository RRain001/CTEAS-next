#pragma once
// S4-R1c7b: use existing G17C3 original station physical kernels on genuine
// 2SS+1US source, without creating a site-specific STHEOR formula.
// Original missing station wind remains invalid, not zero/calm.
#include "cteas/p6/p6g_g47_real_water_post_slope.hpp"
#include "cteas/p6/p6g_g23_file_backed_stheor_inter2.hpp"
#include <cstddef>
#include <stdexcept>
#include <vector>

namespace cteas::calmet::p6g {
struct G48RealSparseStheor {
    std::vector<G17C3StationDiagi> native_valid_station;
    std::vector<std::size_t> source_valid_surface_ordinals;
    std::size_t original_surface_station_count=0;
    std::size_t missing_wind_skipped=0;
    bool source_p5_raw_wind_unchanged=false;
    bool native_shared_g16_sparse_wind1_equal_to_g42=false;
    // Diagnostic stage data are never authorized G23/G26 production fields.
    std::vector<float> firsthour_inter2_u_unverified;
    std::vector<float> firsthour_inter2_v_unverified;
    bool firsthour_inter2_candidate_unverified=false;
    bool native_g23_inter2_or_g26_ready=false;
};

inline G48RealSparseStheor g48_real_sparse_stheor_first_hour(
    const G19SourceFilePaths& paths,bool explicit_reference_only,
    bool explicit_firsthour_inter2_forensic_only=false) {
    if(!explicit_reference_only)
        throw std::invalid_argument("G48 real station STHEOR requires test-only opt-in");
    // G47 uses exactly accepted G42/G21/G39/G22 C++ kernels.
    const auto g47=g47_actual_noow_water_after_elustr_slope(paths,true);
    auto selected=g41_load_selected_noow_water_first_hour_source(paths,true);
    const auto raw=selected.source.surface.hourly.front();
    const auto repaired=g43_original_comp_missfc_source_only(
        selected,selected.source.surface.hourly.front(),true);
    if(!g47.source_raw_p5_unchanged||
       !repaired.source_comp_missfc_complete||
       repaired.G14_G26_production_accepted||
       raw.by_station.size()!=2||
       selected.source.stations.upper.size()!=1)
        throw std::logic_error("G48 genuine source and original MISSFC disconnected");
    // Reconstitute the SAME source-owned original COMP internal nonwind
    // materialization. No change to raw P5 observation records.
    selected.source.surface.hourly.front()=repaired.original_comp_resolved;
    for(std::size_t s=0;s<raw.by_station.size();++s) {
        const auto& before=raw.by_station[s];
        const auto& after=selected.source.surface.hourly.front().by_station[s];
        if(before.wind_valid!=after.wind_valid||
           before.wind_speed_mps!=after.wind_speed_mps||
           before.wind_direction_deg!=after.wind_direction_deg||
           before.precip_code!=after.precip_code)
            throw std::logic_error("G48 illegally replaced raw wind/precip");
    }
    auto scheduler=selected.source.make_scheduler();
    auto frame=scheduler.preview_next_hour();
    if(frame.hour_index!=0||
       frame.input.end!=g47.end||
       frame.input.end!=g47.thermal.native_heat.heat.end||
       frame.input.end!=g47.thermal.native_fradj.end)
        throw std::logic_error("G48 cross-source NOAA first-hour clock drift");
    const auto& original_wind1=
        g47.thermal.native_wind1.native_firstguess;
    // The same source-owned G20/G42 profiles drive BOTH G42 and the
    // existing shared G16 physics, with original missing SS validity
    // unchanged. G16's default production-like entry must fail closed;
    // explicit research source admission must reproduce frozen G42 WIND1
    // elementwise on all real 82x85x9 U/V without an original-wind oracle.
    G16SelectedWindPhysics unmarked(
        g47.thermal.native_wind1.source_profiles);
    bool default_denied=false;
    try {
        auto untouched=frame;
        (void)unmarked.run(p6::NativeHourStage::DiagnoWind1,untouched);
    }catch(const std::invalid_argument&) {
        default_denied=true;
    }
    if(!default_denied)
        throw std::logic_error(
            "G48 G16 unmarked original-missing SURF falsely entered WIND1");
    G16SelectedWindPhysics shared(
        g47.thermal.native_wind1.source_profiles,true);
    const auto accepted=shared.run(
        p6::NativeHourStage::DiagnoWind1,frame);
    if(!accepted.completed||
       accepted.source!=p6::NativeHourSource::NativeCpp||
       !shared.selected_result().wind1_complete)
        throw std::logic_error("G48 shared source-only G16 WIND1 not executed");
    const auto& g16=shared.selected_result().first_guess;
    if(g16.nx!=original_wind1.nx||
       g16.ny!=original_wind1.ny||
       g16.nz!=original_wind1.nz||
       g16.u_mps!=original_wind1.u_mps||
       g16.v_mps!=original_wind1.v_mps)
        throw std::logic_error(
            "G48 shared G16 WIND1 does not equal independently source-validated G42");
    const auto& fradj=g47.thermal.native_fradj.corrected_wind;
    G17B4TwoPassSurfvar twice(
        selected.source.grid,selected.source.stations,
        selected.source.surface,frame.surface,
        selected.surface_controls,true);
    twice.after_wind1_before_fradj(
        frame.input.end,original_wind1.u_mps,original_wind1.v_mps);
    twice.after_fradj_before_heatfx(
        frame.input.end,fradj.u,fradj.v);
    if(twice.final_temperature()!=
       g47.thermal.native_heat.heat.temperature_k)
        throw std::logic_error("G48 real G17B4/G39 source temperatures differ");
    const auto ctrl=g23_source_stheor_station_controls(
        selected.source.original_metinp,
        selected.source_setcom_station_to_upper,
        selected.water_heat_source.reference_heat.coefficients,
        selected.source.stations.surface.size(),true);
    auto native=selected_station_diagi_from_previous_comp(
        frame,twice,g47.thermal.native_heat.heat,ctrl,
        true); // ONLY difference: skip genuine source missing SS wind
    G48RealSparseStheor result;
    result.original_surface_station_count=raw.by_station.size();
    result.native_valid_station=std::move(native);
    for(std::size_t s=0;s<raw.by_station.size();++s) {
        if(raw.by_station[s].wind_valid)
            result.source_valid_surface_ordinals.push_back(s+1);
        else
            ++result.missing_wind_skipped;
    }
    if(result.missing_wind_skipped!=1||
       result.native_valid_station.size()!=1||
       result.source_valid_surface_ordinals.size()!=1||
       result.native_valid_station.front().surface_id!=
         selected.source.stations.surface[
           result.source_valid_surface_ordinals.front()-1].id||
       scheduler.completed_hours()!=0)
        throw std::logic_error(
            "G48 real first-hour original sparse STHEOR count/identity mismatch");
    if(explicit_firsthour_inter2_forensic_only) {
        // G17C3's native actual valid surface station is mapped back into
        // the SAME original SS1..SSn, US1..USm identity space. Missing
        // source wind is never marked valid (nor converted to calm).
        std::vector<unsigned char> source_wind_valid;
        for(const auto& obs:raw.by_station)
            source_wind_valid.push_back(obs.wind_valid?1U:0U);
        const auto merged=merge_g17c3_surface_diagi(
            g47.thermal.native_wind1.source_profiles,
            selected.source.stations,result.native_valid_station,
            source_wind_valid);
        // Source G47 validates the 6970×9 POST-FRADJ+SLOPE grid without
        // reading any original post-INTER2 U/V. Under original IPROG=0,
        // RDWT gives the same physical WO=1 branch as shared G23.
        if(frame.source_controls->iprog!=0)
            throw std::invalid_argument(
                "G48 real INTER2 non-unit source WO remains unsupported");
        const auto nx=static_cast<std::size_t>(frame.grid.nx);
        const auto ny=static_cast<std::size_t>(frame.grid.ny);
        const auto n=nx*ny;
        G16PostSlopeFields corrected;
        corrected.end=frame.input.end;
        corrected.u_mps=g47.slope.post_slope_wind.u;
        corrected.v_mps=g47.slope.post_slope_wind.v;
        if(corrected.u_mps.size()!=9*n||
           corrected.v_mps.size()!=9*n)
            throw std::logic_error("G48 incomplete native source post-SLOPE");
        corrected.observation_weight.assign(9*n,1.f);
        corrected.ub_west_east_mps.resize(18*ny);
        corrected.vb_south_north_mps.resize(18*nx);
        for(std::size_t k=0;k<9;++k) {
            for(std::size_t j=0;j<ny;++j) {
                const auto row=k*n+j*nx,face=k*2*ny+j;
                corrected.ub_west_east_mps[face]=corrected.u_mps[row];
                corrected.ub_west_east_mps[face+ny]=corrected.u_mps[row+nx-1];
            }
            for(std::size_t i=0;i<nx;++i) {
                const auto row=k*n+i,face=k*2*nx+i;
                corrected.vb_south_north_mps[face]=corrected.v_mps[row];
                corrected.vb_south_north_mps[face+nx]=
                    corrected.v_mps[row+(ny-1)*nx];
            }
        }
        shared.provide_post_slope(std::move(corrected));
        shared.provide_selected_diagi_after_wind1(merged);
        const auto inter2=shared.run(
            p6::NativeHourStage::DiagnoInter2,frame);
        if(!inter2.completed||
           inter2.source!=p6::NativeHourSource::NativeCpp||
           !shared.selected_result().inter2_complete)
            throw std::logic_error(
                "G48 original-source real INTER2 candidate not computed");
        result.firsthour_inter2_u_unverified=
            shared.selected_result().blended_u.component_mps;
        result.firsthour_inter2_v_unverified=
            shared.selected_result().blended_v.component_mps;
        if(result.firsthour_inter2_u_unverified.size()!=9*n||
           result.firsthour_inter2_v_unverified.size()!=9*n)
            throw std::logic_error("G48 incomplete native full-grid INTER2");
        result.firsthour_inter2_candidate_unverified=true;
    }
    result.source_p5_raw_wind_unchanged=true;
    result.native_shared_g16_sparse_wind1_equal_to_g42=true;
    return result;
}
} // namespace cteas::calmet::p6g
