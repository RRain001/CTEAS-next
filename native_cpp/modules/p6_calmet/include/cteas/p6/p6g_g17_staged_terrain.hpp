#pragma once
// G17A: source-ordered selected terrain stages, reusing the immutable PR #53
// physical FRADJ/SLOPE kernels and G16 native WIND1/INTER2 stages.
// This explicitly controlled-fixture adapter NEVER claims original P6E
// HEATFX, ELUSTR, AIRDEN, COMP, or complete CALMET native hour acceptance.
// Real multi-site thermal P6E state remains mandatory for production.
#include "cteas/p6/p6g_g16_staged_wind.hpp"
#include "cteas/p6/p6g_terrain_hour.hpp"
#include "cteas/p6/p6g_g17b_setcom_airden.hpp"
#include "cteas/p6/p6g_g17b4_iavet_two_pass.hpp"
#include "cteas/p6/diagno_segment.hpp"
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <optional>
#include <stdexcept>
#include <utility>
#include <vector>

namespace cteas::calmet::p6g {

struct G17FradjSource {
    std::chrono::sys_seconds end{};
    TerrainHourProvenance provenance=TerrainHourProvenance::Missing;
    int isurft=-1;
    float domain_temperature_k=0.f,critfn=0.f;
    std::vector<float> lapse_k_per_m,temperature_k;
};
struct G17SlopeHeatSource {
    std::chrono::sys_seconds end{};
    TerrainHourProvenance provenance=TerrainHourProvenance::Missing;
    std::vector<float> sensible_heat_w_m2,temperature_k;
};

class G17SelectedTerrainFixturePhysics final : public MultiHourPhysics {
public:
    G17SelectedTerrainFixturePhysics(G16ObservedProfiles profiles,
                                    TerrainStaticG11 terrain,
                                    G17FradjSource fradj)
        : wind_(std::move(profiles)),terrain_(std::move(terrain)),
          fradj_(std::move(fradj)) {}

    [[nodiscard]] const G16WindStages& wind_stages() const {
        return wind_.selected_result();
    }
    [[nodiscard]] const p6::WindUV& after_fradj() const {
        if(!after_fradj_)throw std::logic_error("G17 FRADJ not yet computed");
        return *after_fradj_;
    }
    [[nodiscard]] const p6::WindUV& after_slope() const {
        if(!after_slope_)throw std::logic_error("G17 SLOPE not yet computed");
        return *after_slope_;
    }
    // The G17D tail must only be called on the selected original READGE
    // HTFAC=1 branch. GEO.DAT is currently constrained to HTFAC=1 by the
    // P6G source reader; manually constructed grids need this explicit
    // TEST-only declaration, never an inferred default.
    void provide_selected_readge_htfac_fixture(float htfac,bool explicitly_test_only) {
        if(wind_.selected_result().wind1_complete||htfac_selected_||
           !explicitly_test_only||htfac!=1.f)
            throw std::invalid_argument("G17D source GEO HTFAC=1 scope not proven");
        htfac_selected_=true;
    }
    [[nodiscard]] const p6::FinalWindSegment& selected_final_wind() const {
        if(!final_wind_)throw std::logic_error("G17D final W unavailable before mass segment");
        return *final_wind_;
    }
    [[nodiscard]] const p6::SmoothInput& selected_post_inter2_windbc() const {
        if(!smooth_input_)throw std::logic_error("G17D second WINDBC not completed");
        return *smooth_input_;
    }
    // Bind the actual stage WIND1 vector to the FIRST original SURFVAR
    // before FRADJ. Do not let a separately prepared wind or temperature
    // array masquerade as this model hour.
    void prepare_original_iavet1_before_fradj(G17B4TwoPassSurfvar& source) {
        if(!wind_.selected_result().wind1_complete||after_fradj_||
           heat_||airden_||iavet1_final_||
           source.first_ready()||source.second_ready()||
           source.end()!=current_hour_)
            throw std::logic_error(
                "G17B4 first SURFVAR outside source WIND1→FRADJ stage");
        const auto& first=wind_.selected_result().first_guess;
        source.after_wind1_before_fradj(current_hour_,first.u_mps,first.v_mps);
        fradj_.temperature_k=source.first_temperature();
    }

    // Original CALMET performs two different IAVET=1 SURFVAR calls:
    // 1. immediately after WIND1 and before FRADJ;
    // 2. using the corrected FRADJ wind before HEATFX/AIRDEN.
    // The first temperature MUST match the FRADJ input and the stored
    // source WIND1. The second temperature is calculated HERE using this
    // stage's actual FRADJ-adjusted U/V, not an unrelated fixture.
    void finish_original_iavet1_after_fradj(G17B4TwoPassSurfvar& source) {
        if(!after_fradj_||after_slope_||heat_||airden_||iavet1_final_)
            throw std::logic_error("G17B4 second SURFVAR outside FRADJ→HEATFX");
        if(source.end()!=current_hour_||!source.first_ready()||
           source.second_ready()||
           source.first_temperature()!=fradj_.temperature_k||
           !source.first_stage_wind_matches(
               wind_.selected_result().first_guess.u_mps,
               wind_.selected_result().first_guess.v_mps))
            throw std::invalid_argument(
                "G17B4 first original SURFVAR does not match the current native WIND1/FRADJ");
        source.after_fradj_before_heatfx(
            current_hour_,after_fradj_->u,after_fradj_->v);
        iavet1_final_=source.final_temperature();
    }

    // Selected source AIRDEN L2094-L2098 is now available when the caller
    // explicitly supplies the SAME validated SURFVAR temperature used by
    // FRADJ. Without this real-observation handoff AIRDEN remains false.
    void prepare_selected_airden(const MultiHourFrame& frame,
                                 const std::vector<float>& surfvar_temperature_k) {
        if(!after_fradj_||after_slope_||airden_)
            throw std::logic_error("G17B AIRDEN outside FRADJ→SLOPE window");
        verify_hour(frame);
        const auto& correct_final=iavet1_final_
            ?*iavet1_final_:fradj_.temperature_k;
        if(surfvar_temperature_k!=correct_final)
            throw std::invalid_argument(
                "G17B AIRDEN TEMP2D differs from final source SURFVAR");
        const auto nearest=source_setcom_nears(frame.grid,frame.stations);
        airden_=source_airden_nears(
            nearest,surfvar_temperature_k,frame.surface);
    }
    [[nodiscard]] const std::vector<float>& selected_air_density() const {
        if(!airden_)throw std::logic_error("G17B native AIRDEN not computed");
        return *airden_;
    }

    // G17 consumes QH only after FRADJ. A fixture is deliberately supplied
    // outside the still-unimplemented HEATFX/AIRDEN/ELUSTR callbacks. An
    // invalid/missing source fails closed; the full hourly scheduler cannot
    // accept the partial adapter because those stages return Unknown/false.
    void provide_slope_heat(G17SlopeHeatSource source) {
        if(!after_fradj_||after_slope_||heat_)
            throw std::logic_error("G17 heat supplied outside FRADJ→SLOPE window");
        if(source.end!=current_hour_ ||
           source.provenance!=TerrainHourProvenance::SyntheticReferenceFixture)
            throw std::invalid_argument("G17 unvalidated or wrong-hour heat input");
        const auto n=static_cast<std::size_t>(terrain_.nx)*
                     static_cast<std::size_t>(terrain_.ny);
        require_array(source.sensible_heat_w_m2,n);
        require_array(source.temperature_k,n);
        for(float t:source.temperature_k)
            if(t<=0.f)throw std::invalid_argument("G17 invalid surface T");
        // IAVET=0 reuses one SURFVAR TEMP2D. Original IAVET=1 uses the
        // WIND1 TEMP2D for FRADJ and a DIFFERENT post-FRADJ TEMP2D for
        // HEATFX/AIRDEN/SLOPE; require verified second-pass state.
        const auto& required_final=iavet1_final_
            ?*iavet1_final_:fradj_.temperature_k;
        if(source.temperature_k!=required_final)
            throw std::invalid_argument(
                "G17 heat TEMP2D differs from correct final source SURFVAR");
        heat_=std::move(source);
    }

    // Attach the original STHEOR/ELUSTR2/MIXHTST-capped SS columns only
    // after first WINDBC and before INTER2; neutral WIND1 is unchanged.
    void provide_selected_diagi_before_inter2(
        const G16ObservedProfiles& selected) {
        if(!first_windbc_||wind_.selected_result().inter2_complete)
            throw std::logic_error("G17 DIAGI not after source first WINDBC");
        wind_.provide_selected_diagi_after_wind1(selected);
    }

    p6::NativeHourStageResult run(p6::NativeHourStage stage,
                                  MultiHourFrame& frame) override {
        if(stage==p6::NativeHourStage::DiagnoWind1){
            if(wind_.selected_result().wind1_complete)
                throw std::logic_error("G17 WIND1 reused");
            if(terrain_.nx!=frame.grid.nx||terrain_.ny!=frame.grid.ny ||
               terrain_.spacing_m!=frame.grid.grid_km*1000.f ||
               terrain_.landuse!=frame.grid.landuse ||
               terrain_.terrain_m!=frame.grid.terrain_m ||
               terrain_.water_first!=frame.grid.iwat1 ||
               terrain_.water_last!=frame.grid.iwat2)
                throw std::invalid_argument("G17 TERSET not from current GEO");
            auto result=wind_.run(stage,frame);
            if(result.completed)current_hour_=frame.input.end;
            return result;
        }
        if(stage==p6::NativeHourStage::DiagnoFradj)
            return do_fradj(frame);
        if(stage==p6::NativeHourStage::DiagnoAirden){
            verify_hour(frame);
            return airden_
                ?p6::NativeHourStageResult{p6::NativeHourSource::NativeCpp,true}
                :p6::NativeHourStageResult{p6::NativeHourSource::Unknown,false};
        }
        if(stage==p6::NativeHourStage::DiagnoSlope)
            return do_slope(frame);
        if(stage==p6::NativeHourStage::DiagnoWindbcFirstGuess)
            return first_windbc(frame);
        if(stage==p6::NativeHourStage::DiagnoInter2){
            if(!first_windbc_)throw std::logic_error(
                "G17 INTER2 before first source WINDBC");
            return wind_.run(stage,frame);
        }
        if(stage==p6::NativeHourStage::DiagnoWindbcPostInter2Htfac1)
            return htfac_selected_
                ?second_windbc(frame)
                :p6::NativeHourStageResult{p6::NativeHourSource::Unknown,false};
        if(stage==p6::NativeHourStage::DiagnoSmoothDivcelW)
            return htfac_selected_
                ?final_mass_w(frame)
                :p6::NativeHourStageResult{p6::NativeHourSource::Unknown,false};
        // Full HEATFX/ELUSTR and DIAGI stability-dependent SIMILT are
        // NOT implemented; neither are COMP, P6F, final mass-consistency.
        return {p6::NativeHourSource::Unknown,false};
    }
private:
    static void require_array(const std::vector<float>& a,std::size_t n) {
        if(a.size()!=n)throw std::invalid_argument("G17 missing source field");
        for(float v:a)
            if(!std::isfinite(v))
                throw std::invalid_argument("G17 nonfinite source field");
    }
    void verify_hour(const MultiHourFrame& frame) const {
        if(frame.input.end!=current_hour_ || frame.surface.end!=current_hour_ ||
           fradj_.end!=current_hour_)
            throw std::invalid_argument("G17 terrain forcing has wrong model hour");
        if(!frame.source_controls)
            throw std::invalid_argument("G17 missing original met.inp ZFACE");
    }
    p6::NativeHourStageResult do_fradj(const MultiHourFrame& frame) {
        if(!wind_.selected_result().wind1_complete||after_fradj_||heat_||
           first_windbc_)
            throw std::logic_error("G17 FRADJ invalid source stage ordering");
        verify_hour(frame);
        if(fradj_.provenance!=TerrainHourProvenance::SyntheticReferenceFixture||
           fradj_.isurft!=-1)
            throw std::invalid_argument("G17 FRADJ forcing is not accepted fixture");
        const auto n=static_cast<std::size_t>(terrain_.nx)*
                     static_cast<std::size_t>(terrain_.ny);
        require_array(fradj_.lapse_k_per_m,n);
        require_array(fradj_.temperature_k,n);
        const auto& first=wind_.selected_result().first_guess;
        const std::vector<float> zface(frame.source_controls->zface_m.begin(),
                                       frame.source_controls->zface_m.end());
        p6::WindUV initial{first.u_mps,first.v_mps};
        // Original CALMET source kernel, same as G11; no reimplementation.
        auto calculated=p6::froude_adjust(
            terrain_.nx,terrain_.ny,9,terrain_.spacing_m,terrain_.spacing_m,
            terrain_.terrain_m,terrain_.hmax_m,fradj_.lapse_k_per_m,
            fradj_.temperature_k,fradj_.isurft,
            fradj_.domain_temperature_k,fradj_.critfn,
            zface,std::move(initial));
        after_fradj_=std::move(calculated);
        return {p6::NativeHourSource::NativeCpp,true};
    }
    p6::NativeHourStageResult do_slope(const MultiHourFrame& frame) {
        if(!after_fradj_||!heat_||after_slope_||first_windbc_)
            throw std::logic_error("G17 SLOPE without FRADJ and explicit QH");
        verify_hour(frame);
        const auto n=static_cast<std::size_t>(terrain_.nx)*
                     static_cast<std::size_t>(terrain_.ny);
        require_array(heat_->sensible_heat_w_m2,n);
        require_array(heat_->temperature_k,n);
        p6::SlopeInput slope;
        slope.nx=terrain_.nx;slope.ny=terrain_.ny;slope.nz=9;
        slope.dx_m=terrain_.spacing_m;slope.dy_m=terrain_.spacing_m;
        slope.water_first=terrain_.water_first;
        slope.water_last=terrain_.water_last;
        slope.isurft=fradj_.isurft;
        slope.domain_temperature_k=fradj_.domain_temperature_k;
        slope.zface_m.assign(frame.source_controls->zface_m.begin(),
                             frame.source_controls->zface_m.end());
        slope.terrain_m=terrain_.terrain_m;
        slope.hmax_m=terrain_.hmax_m;slope.hmin_m=terrain_.hmin_m;
        slope.disthmax_m=terrain_.dist_hmax_m;
        slope.disthmin_m=terrain_.dist_hmin_m;
        slope.sensible_heat_w_m2=heat_->sensible_heat_w_m2;
        slope.surface_temperature_k=heat_->temperature_k;
        slope.landuse=terrain_.landuse;
        const auto addition=p6::compute_original_slope_scoped(slope);
        auto corrected=*after_fradj_;
        if(corrected.u.size()!=addition.u_mps.size()||
           corrected.v.size()!=addition.v_mps.size())
            throw std::invalid_argument("G17 FRADJ/SLOPE array geometry mismatch");
        for(std::size_t index=0;index<corrected.u.size();++index){
            corrected.u[index]+=addition.u_mps[index];
            corrected.v[index]+=addition.v_mps[index];
            if(!std::isfinite(corrected.u[index])||
               !std::isfinite(corrected.v[index]))
                throw std::invalid_argument("G17 SLOPE produced nonfinite winds");
        }
        after_slope_=std::move(corrected);
        return {p6::NativeHourSource::NativeCpp,true};
    }
    p6::NativeHourStageResult first_windbc(const MultiHourFrame& frame) {
        if(!after_slope_||first_windbc_)
            throw std::logic_error("G17 first WINDBC before source SLOPE");
        verify_hour(frame);
        const auto nx=static_cast<std::size_t>(terrain_.nx);
        const auto ny=static_cast<std::size_t>(terrain_.ny);
        const auto n=nx*ny;
        G16PostSlopeFields handoff;
        handoff.end=current_hour_;
        handoff.u_mps=after_slope_->u;
        handoff.v_mps=after_slope_->v;
        // For the currently accepted IPROG=0 route RDWT supplies WO=1;
        // other spatial WO cases cannot be silently emulated.
        if(frame.source_controls->iprog!=0)
            throw std::invalid_argument("G17 first WINDBC needs source WO");
        handoff.observation_weight.assign(n*9,1.f);
        handoff.ub_west_east_mps.resize(18*ny);
        handoff.vb_south_north_mps.resize(18*nx);
        for(std::size_t k=0;k<9;++k){
            for(std::size_t j=0;j<ny;++j){
                const auto row=k*n+j*nx;
                handoff.ub_west_east_mps[k*2*ny+j]=handoff.u_mps[row];
                handoff.ub_west_east_mps[k*2*ny+ny+j]=handoff.u_mps[row+nx-1];
            }
            for(std::size_t i=0;i<nx;++i){
                const auto row=k*n+i;
                handoff.vb_south_north_mps[k*2*nx+i]=handoff.v_mps[row];
                handoff.vb_south_north_mps[k*2*nx+nx+i]=
                    handoff.v_mps[row+(ny-1)*nx];
            }
        }
        wind_.provide_post_slope(std::move(handoff));
        first_windbc_=true;
        return {p6::NativeHourSource::NativeCpp,true};
    }
    p6::NativeHourStageResult second_windbc(const MultiHourFrame& frame) {
        verify_hour(frame);
        if(!htfac_selected_||!first_windbc_||
           !wind_.selected_result().inter2_complete||
           smooth_input_||final_wind_)
            throw std::logic_error("G17D second WINDBC requires accepted INTER2/HTFAC=1");
        const auto& first=wind_.selected_result();
        const auto nx=static_cast<std::size_t>(terrain_.nx);
        const auto ny=static_cast<std::size_t>(terrain_.ny);
        const auto plane=nx*ny;
        const auto count=plane*9;
        const auto& u=first.blended_u.component_mps;
        const auto& v=first.blended_v.component_mps;
        require_array(u,count);require_array(v,count);
        p6::SmoothInput input;
        input.nx=terrain_.nx;input.ny=terrain_.ny;input.nz=9;
        input.lake_breeze=false; // source selected LLBREZE=F, not generalized
        input.passes_per_layer.assign(frame.source_controls->nsmth.begin(),
                                       frame.source_controls->nsmth.end());
        input.u_mps=u;input.v_mps=v;
        input.ub_west_east_mps.resize(18*ny);
        input.vb_south_north_mps.resize(18*nx);
        // Original CALMET L6092-6101: HTFAC>0 performs SECOND WINDBC(U,V)
        // after INTER2, overwriting the pre-INTER2 boundary snapshots.
        // The G16 original_ub/original_vb arrays remain unchanged for audit.
        for(std::size_t k=0;k<9;++k) {
            for(std::size_t j=0;j<ny;++j) {
                const auto off=k*plane+j*nx;
                input.ub_west_east_mps[k*2*ny+j]=u[off];
                input.ub_west_east_mps[k*2*ny+ny+j]=u[off+nx-1];
            }
            for(std::size_t i=0;i<nx;++i) {
                const auto off=k*plane+i;
                input.vb_south_north_mps[k*2*nx+i]=v[off];
                input.vb_south_north_mps[k*2*nx+nx+i]=v[off+(ny-1)*nx];
            }
        }
        smooth_input_=std::move(input);
        return {p6::NativeHourSource::NativeCpp,true};
    }
    p6::NativeHourStageResult final_mass_w(MultiHourFrame& frame) {
        verify_hour(frame);
        if(!smooth_input_||final_wind_||
           !wind_.selected_result().inter2_complete||
           frame.source_controls->iobr!=0)
            throw std::logic_error("G17D final SMOOTH/DIVCEL/W outside source stage");
        std::vector<float> dz;
        dz.reserve(9);
        for(std::size_t k=0;k<9;++k) {
            const auto lo=frame.source_controls->zface_m[k];
            const auto hi=frame.source_controls->zface_m[k+1];
            if(!std::isfinite(lo)||!std::isfinite(hi)||hi<=lo)
                throw std::invalid_argument("G17D invalid source ZFACE/DZ");
            dz.push_back(hi-lo);
        }
        // Exact PR #53 source-checked final segment, no duplicated physics
        // and no replacement of previous COMP ZI/ZICONV/DPTT state.
        final_wind_=p6::original_smooth_divcel_w(
            *smooth_input_,terrain_.spacing_m,terrain_.spacing_m,dz,false);
        frame.fields.u_mps=final_wind_->u_mps;
        frame.fields.v_mps=final_wind_->v_mps;
        frame.fields.w_face_mps=final_wind_->w_face_mps;
        return {p6::NativeHourSource::NativeCpp,true};
    }
    G16SelectedWindPhysics wind_;
    TerrainStaticG11 terrain_;
    G17FradjSource fradj_;
    std::chrono::sys_seconds current_hour_{};
    std::optional<p6::WindUV> after_fradj_,after_slope_;
    std::optional<std::vector<float>> iavet1_final_;
    std::optional<G17SlopeHeatSource> heat_;
    std::optional<std::vector<float>> airden_;
    bool first_windbc_=false,htfac_selected_=false;
    std::optional<p6::SmoothInput> smooth_input_;
    std::optional<p6::FinalWindSegment> final_wind_;
};
} // namespace cteas::calmet::p6g
