#pragma once
// G16A: stage-scoped C++ CALMET WIND1 and INTER2, in PR #53's original
// DIAGNO stage positions. Never blend before the post-FRADJ/SLOPE boundary.
// This is a selected-kernel adapter, NOT a complete hourly CALMET solver.
// PREPDI, terrain/thermal, WINDBC, COMP and P6F remain fail-closed until
// independently integrated. Source/oracle fields are never accepted as output.
#include "cteas/p6/p6g_unified_hourly.hpp"
#include "cteas/p6/p6g_multi_wind1_firstguess.hpp"
#include "cteas/p6/inter2_selected.hpp"
#include <chrono>
#include <cmath>
#include <cstddef>
#include <optional>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace cteas::calmet::p6g {
struct G16ObservedProfiles {
    std::chrono::sys_seconds end{};
    // Station major order in each layer: SS1..SSn, US1..USn (met.inp).
    // Must be supplied by source-validated SIMILT/VERTAV/PREPDI upstream.
    // WIND1 source SIMILT: neutral and uncapped, calmet.for L36171.
    std::vector<float> wind1_u_mps,wind1_v_mps;
    std::vector<unsigned char> wind1_present;
    // INTER2 source DIAGI: stability-dependent SIMILT capped at MIXHTST ZI,
    // upper soundings from hourly PREPDI; NOT interchangeable with WIND1.
    std::vector<float> inter2_u_mps,inter2_v_mps;
    std::vector<unsigned char> inter2_present;
    std::vector<int> station_ids; // matching met.inp SS/US ordinal identities
};
struct G16PostSlopeFields {
    std::chrono::sys_seconds end{};
    // Mandatory source-computed fields AFTER FRADJ, HEATFX, SLOPE and first
    // WINDBC, never a substitute built by copying the WIND1 first guess.
    std::vector<float> u_mps,v_mps,observation_weight;
    // Original L5748 first WINDBC boundary, saved BEFORE INTER2.
    // k-major; WEST/EAST: k*2*ny + [0..ny-1] / [ny..2ny-1]
    // SOUTH/NORTH: k*2*nx + [0..nx-1] / [nx..2nx-1].
    std::vector<float> ub_west_east_mps,vb_south_north_mps;
};
struct G16WindStages {
    std::chrono::sys_seconds end{};
    Wind1MultiField first_guess;
    p6::Inter2SelectedOutput blended_u,blended_v;
    std::vector<float> original_ub_west_east_mps,original_vb_south_north_mps;
    bool wind1_complete=false,inter2_complete=false;
};
class G16SelectedWindPhysics final : public MultiHourPhysics {
public:
    explicit G16SelectedWindPhysics(G16ObservedProfiles profiles)
        : profiles_(std::move(profiles)) {}

    const G16WindStages& selected_result() const noexcept {return stage_;}
    // Explicit post-SLOPE handoff is an independent physical requirement.
    // It cannot be silently synthesized from the WIND1 preliminary field.
    void provide_post_slope(G16PostSlopeFields input) {
        if(!stage_.wind1_complete||stage_.inter2_complete||corrected_)
            throw std::logic_error("G16 post-SLOPE handoff out of source order");
        if(input.end!=stage_.end)
            throw std::invalid_argument("G16 post-SLOPE wind has wrong UTC hour");
        const auto nx=static_cast<std::size_t>(stage_.first_guess.nx);
        const auto ny=static_cast<std::size_t>(stage_.first_guess.ny);
        const auto cells=nx*ny;
        require_finite(input.u_mps,cells*9,"post-SLOPE U");
        require_finite(input.v_mps,cells*9,"post-SLOPE V");
        require_finite(input.observation_weight,cells*9,"post-SLOPE WO");
        require_finite(input.ub_west_east_mps,9*2*ny,"pre-INTER2 UB");
        require_finite(input.vb_south_north_mps,9*2*nx,"pre-INTER2 VB");
        for(float w:input.observation_weight)
            if(w<0.f||w>1.f)
                throw std::invalid_argument("G16 original WO outside 0..1");
        for(std::size_t k=0;k<9;++k) {
            for(std::size_t j=0;j<ny;++j) {
                const auto row=k*cells+j*nx;
                const auto face=k*2*ny+j;
                if(input.ub_west_east_mps[face]!=input.u_mps[row]||
                   input.ub_west_east_mps[face+ny]!=input.u_mps[row+nx-1])
                    throw std::invalid_argument(
                        "G16 first WINDBC U not from pre-INTER2 corrected U");
            }
            for(std::size_t i=0;i<nx;++i) {
                const auto row=k*cells+i;
                const auto face=k*2*nx+i;
                if(input.vb_south_north_mps[face]!=input.v_mps[row]||
                   input.vb_south_north_mps[face+nx]!=
                       input.v_mps[row+(ny-1)*nx])
                    throw std::invalid_argument(
                        "G16 first WINDBC V not from pre-INTER2 corrected V");
            }
        }
        corrected_=std::move(input);
    }

    // One source-selected post-MIXHTST DIAGI refresh per hour. WIND1
    // stays neutral and upper-air PREPDI columns stay independently owned.
    void provide_selected_diagi_after_wind1(
        const G16ObservedProfiles& observed) {
        if(!stage_.wind1_complete||stage_.inter2_complete||diagi_refreshed_||
           !corrected_||observed.end!=stage_.end||
           observed.station_ids!=profiles_.station_ids||
           observed.wind1_u_mps!=profiles_.wind1_u_mps||
           observed.wind1_v_mps!=profiles_.wind1_v_mps||
           observed.wind1_present!=profiles_.wind1_present)
            throw std::invalid_argument("G16 source DIAGI/WIND1 identity or ordering invalid");
        const auto total=profiles_.station_ids.size();
        const auto ns=surface_count_;
        if(ns==0||ns>=total||
           observed.inter2_u_mps.size()!=9*total||
           observed.inter2_v_mps.size()!=9*total||
           observed.inter2_present.size()!=9*total)
            throw std::invalid_argument("G16 source DIAGI dimensions invalid");
        // Retain upper columns from the existing source PREPDI, not a
        // separate interpolated or differently stamped observation.
        for(std::size_t k=0;k<9;++k)
            for(std::size_t i=ns;i<total;++i) {
                const auto p=k*total+i;
                if(observed.inter2_u_mps[p]!=profiles_.inter2_u_mps[p]||
                   observed.inter2_v_mps[p]!=profiles_.inter2_v_mps[p]||
                   observed.inter2_present[p]!=profiles_.inter2_present[p])
                    throw std::invalid_argument("G16 DIAGI would replace PREPDI UP columns");
            }
        profiles_.inter2_u_mps=observed.inter2_u_mps;
        profiles_.inter2_v_mps=observed.inter2_v_mps;
        profiles_.inter2_present=observed.inter2_present;
        diagi_refreshed_=true;
    }

    p6::NativeHourStageResult run(
        p6::NativeHourStage stage,MultiHourFrame& hour) override {
        if(stage==p6::NativeHourStage::DiagnoWind1)
            return do_wind1(hour);
        if(stage==p6::NativeHourStage::DiagnoInter2)
            return do_inter2(hour);
        // Explicit NOT completed: no fake PREPDI, FRADJ, HEATFX, SLOPE,
        // WINDBC, SMOOTH/W, COMP, CGAMMA, TEMP3D or output stages.
        return {p6::NativeHourSource::Unknown,false};
    }
private:
    static void require_finite(const std::vector<float>& v,
                               std::size_t count,const char* label) {
        if(v.size()!=count)
            throw std::invalid_argument(std::string("G16 bad size for ")+label);
        for(float x:v)
            if(!std::isfinite(x))
                throw std::invalid_argument(std::string("G16 nonfinite ")+label);
    }
    const OriginalWindControls& source(const MultiHourFrame& hour) const {
        if(!hour.source_controls)
            throw std::invalid_argument("G16 missing authoritative met.inp controls");
        const auto& controls=*hour.source_controls;
        if(controls.iextrp!=-4||controls.noobs!=0||controls.iprog!=0||
           controls.lvary||controls.iobr!=0||
           (controls.icalm!=0&&controls.icalm!=1))
            throw std::invalid_argument("G16 unsupported original wind controls");
        return controls;
    }
    p6::NativeHourStageResult do_wind1(MultiHourFrame& hour) {
        if(stage_.wind1_complete||corrected_)
            throw std::logic_error("G16 WIND1 cannot be repeated or reordered");
        const auto& controls=source(hour);
        const auto ns=hour.stations.surface.size();
        const auto nu=hour.stations.upper.size();
        const auto total=ns+nu;
        const auto count=total*9;
        if(ns<1||nu<1||total>479||
           profiles_.end!=hour.input.end||hour.surface.end!=hour.input.end||
           hour.surface.by_station.size()!=ns||
           hour.input.upper.size()!=nu)
            throw std::invalid_argument("G16 WIND1 station/time mismatch");
        require_finite(profiles_.wind1_u_mps,count,"neutral WIND1 station U");
        require_finite(profiles_.wind1_v_mps,count,"neutral WIND1 station V");
        require_finite(profiles_.inter2_u_mps,count,"DIAGI INTER2 station U");
        require_finite(profiles_.inter2_v_mps,count,"DIAGI INTER2 station V");
        if(profiles_.wind1_present.size()!=count||
           profiles_.inter2_present.size()!=count||
           profiles_.station_ids.size()!=total)
            throw std::invalid_argument("G16 WIND1 missing station IDs or flags");
        for(std::size_t i=0;i<ns;++i)
            if(profiles_.station_ids[i]!=hour.stations.surface[i].id)
                throw std::invalid_argument("G16 WIND1 shuffled SURF identity");
        for(std::size_t i=0;i<nu;++i)
            if(profiles_.station_ids[ns+i]!=hour.stations.upper[i].id)
                throw std::invalid_argument("G16 WIND1 shuffled UP identity");
        Wind1MultiInput input;
        input.nx=hour.grid.nx;input.ny=hour.grid.ny;input.nz=9;
        input.spacing_m=hour.grid.grid_km*1000.f;
        input.surface_count=static_cast<int>(ns);
        input.upper_count=static_cast<int>(nu);
        input.icalm=controls.icalm;
        input.vertical_bias.assign(controls.bias.begin(),controls.bias.end());
        input.station_u_mps=profiles_.wind1_u_mps;
        input.station_v_mps=profiles_.wind1_v_mps;
        input.present=profiles_.wind1_present;
        for(std::size_t i=0;i<ns;++i){
            const auto& obs=hour.surface.by_station[i];
            if(!obs.wind_valid||!std::isfinite(obs.wind_speed_mps))
                throw std::invalid_argument("G16 missing original SURF wind for WIND1");
            input.surface_speeds_mps.push_back(obs.wind_speed_mps);
            input.station_x_m.push_back(hour.stations.surface[i].local_x_m);
            input.station_y_m.push_back(hour.stations.surface[i].local_y_m);
        }
        for(const auto& us:hour.stations.upper){
            input.station_x_m.push_back(us.local_x_m);
            input.station_y_m.push_back(us.local_y_m);
        }
        const auto result=multi_station_wind1_firstguess(input);
        stage_.end=hour.input.end;
        stage_.first_guess=result;
        surface_count_=ns;
        stage_.wind1_complete=true;
        return {p6::NativeHourSource::NativeCpp,true};
    }
    p6::NativeHourStageResult do_inter2(MultiHourFrame& hour) {
        if(!stage_.wind1_complete||stage_.inter2_complete||!corrected_||
           !diagi_refreshed_)
            throw std::logic_error(
                "G16 INTER2 requires source DIAGI STHEOR post-MIXHTST station columns and corrected post-SLOPE wind");
        const auto& controls=source(hour);
        const auto cells=static_cast<std::size_t>(hour.grid.nx)*
                         static_cast<std::size_t>(hour.grid.ny);
        const auto count=cells*9;
        if(hour.input.end!=stage_.end||corrected_->end!=stage_.end)
            throw std::invalid_argument("G16 INTER2 cross-hour corrected state");
        require_finite(corrected_->u_mps,count,"corrected U");
        require_finite(corrected_->v_mps,count,"corrected V");
        require_finite(corrected_->observation_weight,count,"physical WO");
        const auto ns=hour.stations.surface.size();
        const auto nu=hour.stations.upper.size();
        const auto total=ns+nu;
        p6::Inter2SelectedInput in;
        in.nx=hour.grid.nx;in.ny=hour.grid.ny;in.nz=9;
        in.nstations=static_cast<int>(total);
        in.dx_m=hour.grid.grid_km*1000.f;in.dy_m=in.dx_m;
        in.rmin_km=controls.rmin_km;in.rmax1_km=controls.rmax1_km;
        in.rmax2_km=controls.rmax2_km;in.rmax3_km=controls.rmax3_km;
        in.r1_km=controls.r1_km;in.r2_km=controls.r2_km;
        in.lvary=controls.lvary;
        in.landuse=hour.grid.landuse;
        in.water_first=hour.grid.iwat1;in.water_last=hour.grid.iwat2;
        for(const auto& s:hour.stations.surface){
            in.station_x_km.push_back(s.local_x_m*0.001f);
            in.station_y_km.push_back(s.local_y_m*0.001f);
        }
        for(const auto& s:hour.stations.upper){
            in.station_x_km.push_back(s.local_x_m*0.001f);
            in.station_y_km.push_back(s.local_y_m*0.001f);
        }
        for(std::size_t k=0;k<9;++k){
            if(controls.nintr2[k]<1)
                throw std::invalid_argument("G16 invalid original NINTR2");
            in.nintrp_per_layer.push_back(
                std::min(controls.nintr2[k],static_cast<int>(total)));
        }
        in.observation_weight=corrected_->observation_weight;
        const auto make_component=[&](const std::vector<float>& station,
                                      const std::vector<float>& corrected) {
            in.station_component_mps=station;
            // Explicit original EDIT/EDITL to distinguish missing observations.
            for(std::size_t k=0;k<9;++k)
                for(std::size_t l=0;l<total;++l)
                    if(!profiles_.inter2_present[k*total+l])
                        in.station_component_mps[k*total+l]=in.edit;
            in.step1_mps=corrected;
            return p6::original_inter2_selected(in);
        };
        // Never re-use the neutral WIND1 profile as the DIAGI/INTER2
        // stability and mixing-height limited observation. This was a
        // source-level ambiguity in the old G8 selected-source bridge.
        const auto u=make_component(profiles_.inter2_u_mps,corrected_->u_mps);
        const auto v=make_component(profiles_.inter2_v_mps,corrected_->v_mps);
        // Preserve original L5748 snapshots for later SMOOTH/DIVCEL/W;
        // do not recompute lateral boundaries from INTER2-blended U/V.
        stage_.original_ub_west_east_mps=corrected_->ub_west_east_mps;
        stage_.original_vb_south_north_mps=corrected_->vb_south_north_mps;
        stage_.blended_u=u;
        stage_.blended_v=v;
        stage_.inter2_complete=true;
        return {p6::NativeHourSource::NativeCpp,true};
    }
    G16ObservedProfiles profiles_;
    G16WindStages stage_{};
    std::optional<G16PostSlopeFields> corrected_;
    bool diagi_refreshed_=false;
    std::size_t surface_count_=0;
};
} // namespace cteas::calmet::p6g
