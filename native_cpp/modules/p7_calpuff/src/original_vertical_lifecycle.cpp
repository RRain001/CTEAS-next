#include "cteas/puff/original_vertical_lifecycle.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <string>
#include <utility>

namespace cteas::puff {
namespace {
void require(bool ok,const char* what) {
    if(!ok) throw std::invalid_argument(std::string("P7 native vertical: ")+what);
}
float real4(double value,const char* name) {
    require(std::isfinite(value),name);
    const float f=static_cast<float>(value);
    require(std::isfinite(f),name);
    return f;
}
}
void OriginalVerticalLifecycle::admit_point(
    int id,const NewPuffInputs& source,const InjectionInputs& injection) {
    require(id>0 && source.source_type==1 && injection.species_count>0,
            "invalid point puff admission");
    require(puffs_.find(id)==puffs_.end(),"duplicate active puff");
    require(real4(source.effective_height_m,"release height")==
            real4(injection.effective_height_m,"injection height"),
            "POINTS1/INJECT inconsistent effective height");
    require(source.stability_class==injection.stability_class,
            "POINTS1/INJECT inconsistent release stability");
    const auto release=new_puff_state(source);
    const auto allocated=inject_emissions(injection);
    NativeVerticalPuffState state;
    state.sigma_y_m=real4(release.sigma_y_m,"source sigma-y");
    state.sigma_z_m=real4(release.sigma_z_m,"source sigma-z");
    state.ziold_m=real4(allocated.previous_mixing_height_m,"ZIOLD");
    state.zimax_m=real4(allocated.unlimited_mixing_height_m,"ZIMAX");
    state.puff_code=allocated.puff_code;
    require(state.sigma_y_m>=0 && state.sigma_z_m>=0 &&
            state.ziold_m>=0 && state.zimax_m>=0 &&
            state.puff_code>0,"invalid initial vertical state");
    for(double mass:allocated.mixed_layer_mass) {
        const auto value=real4(mass,"mixed source mass");
        require(value>=0,"negative mixed source mass");
        state.mass_mixed.push_back(value);
    }
    for(double mass:allocated.above_layer_mass) {
        const auto value=real4(mass,"upper source mass");
        require(value>=0,"negative upper source mass");
        state.mass_above.push_back(value);
    }
    require(state.mass_mixed.size()==static_cast<std::size_t>(injection.species_count) &&
            state.mass_above.size()==state.mass_mixed.size(),
            "incomplete source mass state");
    puffs_.emplace(id,std::move(state));
}
NativeVerticalPuffState OriginalVerticalLifecycle::state(int id) const {
    const auto it=puffs_.find(id);
    if(it==puffs_.end())throw std::out_of_range("unknown vertical puff");
    return it->second;
}
NativeVerticalWind OriginalVerticalLifecycle::sample(
    int id,const OriginalMetHour& met,const Calmet21Static& statics,
    float x,float y,float height) const {
    const auto s=state(id);
    const auto z=real4(height,"native HTMET");
    const auto cell=original_met_cell(x,y,met.nx,met.ny);
    require(cell.offset_0based<met.zi.size() &&
            cell.offset_0based<met.ipgt.size(),
            "METFM1 missing real original surface fields");
    const auto mixing=met.zi[cell.offset_0based];
    const auto stable=met.ipgt[cell.offset_0based];
    require(std::isfinite(mixing) && mixing>=0 &&
            stable>=1 && stable<=6,
            "METFM1 mixing depth or stability invalid");
    PuffExtentInputs input;
    input.puff_code=s.puff_code;
    input.puff=true;
    input.stability_class=stable;
    input.puff_height_m=z;
    input.mixing_height_m=mixing;
    input.sigma_z_begin_m=s.sigma_z_m;
    input.previous_mixing_height_m=s.ziold_m;
    input.maximum_mixing_height_m=s.zimax_m;
    // Original COMP/ZFIND supplies ZFACE(ILAYER:ILAYER+1) to PUFFDZ.
    // The uniform-above-lid ICODE 4/14 path reads both faces, whereas
    // Gaussian cases never needed them. Omitting them silently created an
    // invalid zero-width wind layer for native high-release puffs.
    require(met.nz>0 && statics.cell_face_m.size()==
            static_cast<std::size_t>(met.nz+1),
            "native PUFFDZ requires a complete original ZFACE profile");
    const std::vector<double> faces(statics.cell_face_m.begin(),
                                    statics.cell_face_m.end());
    const int ilayer=find_layer(z,faces);
    require(ilayer>=1 && ilayer<=met.nz,
            "original ZFIND returned out-of-range vertical cell");
    input.layer_bottom_m=statics.cell_face_m.at(static_cast<std::size_t>(ilayer-1));
    input.layer_top_m=statics.cell_face_m.at(static_cast<std::size_t>(ilayer));
    for(float q:s.mass_mixed)input.mixed_layer_mass.push_back(q);
    for(float q:s.mass_above)input.above_layer_mass.push_back(q);
    const auto extent=puff_extent(input);
    const auto wind=original_met_cell_advect(
        met,statics,cell,real4(extent.z_bottom_m,"ZBOT"),
        real4(extent.z_top_m,"ZTOP"));
    return {cell,extent,wind,stable,mixing};
}
void OriginalVerticalLifecycle::commit_wdiv_sigma_z(
    int id,float expected_before,float updated_sigma_z) {
    const auto it=puffs_.find(id);
    if(it==puffs_.end())throw std::out_of_range("original WDIV unknown puff");
    auto& state=it->second;
    require(!state.vmass_pending &&
            state.completed_substeps==state.committed_lid_steps &&
            std::isfinite(expected_before) &&
            state.sigma_z_m==expected_before &&
            std::isfinite(updated_sigma_z) && updated_sigma_z>=0.0F,
            "original WDIV cannot overwrite stale/uncommitted SIGZB");
    state.sigma_z_m=updated_sigma_z;
}
SigmaUpdateResult OriginalVerticalLifecycle::commit_sigma(
    int id,const SigmaUpdateInputs& inputs,
    const SigmaYCurve& yc,const SigmaZCurve& zc,
    const OriginalTerrainSigmaInputs* terrain) {
    const auto it=puffs_.find(id);
    if(it==puffs_.end())throw std::out_of_range("unknown vertical puff");
    const auto& previous=it->second;
    require(previous.vmass_pending &&
            previous.completed_substeps==previous.committed_lid_steps,
            "SETPUF requires VMASS first, once per native substep");
    require(real4(inputs.step.sigma_y_start_m,"sigma-y begin")==previous.sigma_y_m &&
            real4(inputs.step.sigma_z_start_m,"sigma-z begin")==previous.sigma_z_m &&
            inputs.step.puff_code==previous.puff_code,
            "stale or incorrect sigma update state");
    auto next=sigma_update(inputs,yc,zc,terrain);
    const float sy=real4(next.adjust.stored_sigma_y_m,"sigma-y result");
    const float sz=real4(next.adjust.stored_sigma_z_m,"sigma-z result");
    require(sy>=0 && sz>=0,"negative stored native dispersion sigma");
    it->second.sigma_y_m=sy;
    it->second.sigma_z_m=sz;
    ++it->second.completed_substeps;
    return next;
}
void OriginalVerticalLifecycle::commit_lid(
    int id,float native_lid,int native_code) {
    const auto it=puffs_.find(id);
    if(it==puffs_.end())throw std::out_of_range("unknown vertical puff");
    const auto& before=it->second;
    require(std::isfinite(native_lid) && native_lid>=0.0F,
            "nonfinite or negative source-ported HLID");
    require(native_code>0 && native_code<=99,
            "invalid native VMASS-updated puff code");
    require(before.vmass_pending &&
            before.completed_substeps==before.committed_lid_steps+1,
            "COMP lid history requires VMASS then SETPUF exactly once");
    require(native_lid==before.pending_reflecting_lid_m,
            "COMP reflecting lid differs from the pending original VMASS HLID");
    // Fortran REAL*4 AMAX1 exactly matches this max of two float32
    // operands. Keep state authoritative; do not use DGM ZIOLD/ZIMAX here.
    auto after=before;
    after.puff_code=native_code;
    after.zimax_m=std::max(after.zimax_m,native_lid);
    after.ziold_m=native_lid;
    ++after.committed_lid_steps;
    after.vmass_pending=false;
    after.pending_reflecting_lid_m=0.0F;
    it->second=std::move(after);
}
VmassResult OriginalVerticalLifecycle::commit_vmass(
    int id,float pbl,float height_begin,float height_end,
    float sigze,int stable,int tilt) {
    const auto it=puffs_.find(id);
    if(it==puffs_.end())throw std::out_of_range("unknown native vertical puff");
    const auto& before=it->second;
    require(!before.vmass_pending &&
            before.completed_substeps==before.committed_lid_steps,
            "native VMASS must precede SETPUF and follow previous lid commit");
    // Original COMP L10859 VMASS precedes SETPUF L10940; next-step
    // lid update L11391-11398 is a distinct, later phase.
    // Every input is a native production field, NOT a replayed DGM state.
    VmassInputs input;
    input.puff_code=before.puff_code;
    input.stability_class=stable;
    input.plume_tilt=tilt;
    input.pbl_height_m=real4(pbl,"native VMASS DPBL");
    input.height_begin_m=real4(height_begin,"native VMASS ZPB");
    input.height_end_m=real4(height_end,"native VMASS ZPE");
    input.sigma_z_begin_m=before.sigma_z_m;
    input.sigma_z_end_m=real4(sigze,"native VMASS SIGZE");
    input.ziold_m=before.ziold_m;
    input.zimax_m=before.zimax_m;
    input.mass_mixed=before.mass_mixed;
    input.mass_above=before.mass_above;
    const auto updated=original_vmass(input);
    const float lid=updated.reflecting_lid_m;
    require(std::isfinite(lid) && lid>=0.0F,"native VMASS invalid HLID");
    NativeVerticalPuffState after=before;
    after.puff_code=updated.puff_code;
    after.mass_mixed=updated.mass_mixed;
    after.mass_above=updated.mass_above;
    after.zimax_m=updated.zimax_m;
    after.ziold_m=updated.ziold_m;
    after.vmass_pending=true;
    after.pending_reflecting_lid_m=lid;
    it->second=std::move(after);
    return updated;
}
void OriginalVerticalLifecycle::commit_dry(
    int id,const std::vector<float>& expected,
    const std::vector<float>& after_mass) {
    const auto it=puffs_.find(id);
    if(it==puffs_.end())throw std::out_of_range("DRY on absent puff");
    const auto& before=it->second;
    require(before.vmass_pending &&
            before.completed_substeps==before.committed_lid_steps+1,
            "DRY must follow VMASS/SETPUF, precede late lid commit");
    require(before.mass_mixed==expected && expected.size()==after_mass.size(),
            "native DRY source QM differs from staged original VMASS");
    for(std::size_t j=0;j<after_mass.size();++j) {
        require(std::isfinite(after_mass[j]) && after_mass[j]>=0.0F &&
                after_mass[j]<=expected[j],
                "native DRY must not create species mass");
    }
    auto next=before;
    next.mass_mixed=after_mass;
    it->second=std::move(next);
}
void OriginalVerticalLifecycle::retire(int id) {
    if(puffs_.erase(id)!=1U)throw std::out_of_range("retire unknown vertical puff");
}
std::size_t OriginalVerticalLifecycle::active_count()const noexcept {
    return puffs_.size();
}
} // namespace cteas::puff
