#include "cteas/puff/original_vertical_lifecycle.hpp"
#include <array>
#include <bit>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>

namespace {
struct DgmRecord {std::array<std::int32_t,24> i;std::array<float,64> f;};
static_assert(sizeof(DgmRecord)==352);
void require(bool v,const char* msg) {if(!v)throw std::runtime_error(msg);}
template<class F> void rejects(F&& f,const char* why){
    bool threw=false;try{f();}catch(const std::exception&){threw=true;}
    require(threw,why);
}
void local_native_state() {
    using namespace cteas::puff;
    OriginalVerticalLifecycle life;
    NewPuffInputs point;
    point.source_x_km=0.5;point.source_y_km=0.5;
    point.effective_height_m=50;
    point.sigma_y_source_m=1;point.sigma_z_source_m=1;
    point.stability_class=4;
    InjectionInputs injection;
    injection.species_count=1;injection.emission_duration_s=60;
    injection.effective_height_m=50;injection.max_layer_height_m=200;
    injection.mixing_height_m=120;injection.mass_fraction_mixed=1;
    injection.stability_class=4;injection.gaussian_distribution=1;
    injection.emission_rate={2.0};
    life.admit_point(1,point,injection);
    require(life.active_count()==1,"missing native admitted puff");
    const auto before=life.state(1);
    require(before.sigma_z_m==1.0F && before.ziold_m==120.0F &&
            before.zimax_m==120.0F && before.mass_mixed[0]==120.0F &&
            before.mass_above[0]==0.0F && before.puff_code==1,
            "native POINTS1/INJECT REAL4 state not persisted");
    rejects([&]{life.admit_point(1,point,injection);},"duplicate ID allowed");
    OriginalMetHour met;
    met.nx=2;met.ny=2;met.nz=2;met.zi.assign(4,120.0F);
    met.ipgt.assign(4,4);
    met.u.assign(8,1.0F);met.v.assign(8,2.0F);
    Calmet21Static static_met;
    static_met.cell_face_m={0.0F,100.0F,200.0F};
    const auto observed=life.sample(1,met,static_met,0.5F,0.5F,50.0F);
    require(observed.extent.z_top_m==51.0 &&
            observed.extent.z_bottom_m==49.0 &&
            observed.wind.u_ms==1.0 && observed.wind.v_ms==2.0 &&
            observed.cell.ix_1based==1 && observed.cell.iy_1based==1,
            "native PUFFDZ -> ADVECT chain differs on synthetic profile");
    require(life.state(1).completed_substeps==0,"sampling mutated puff state");
    auto yc=[](double sigma,double dx,double dt)->SigmaCurvePoint {
        return {sigma>0?sigma:1+dt*0.1,dt,dx};
    };
    auto zc=[](double sigma,double dx,double dt,double)->SigmaCurvePoint {
        return {sigma>0?sigma:1+dt*0.05,dt,dx};
    };
    SigmaUpdateInputs inputs;
    inputs.step.sigma_y_start_m=1;
    inputs.step.sigma_z_start_m=1;
    inputs.step.puff_height_m=50;
    inputs.step.mid_time_s=30;
    inputs.step.mid_distance_km=0.05;
    inputs.step.puff_code=1;
    rejects([&]{(void)life.commit_sigma(1,inputs,yc,zc);},
            "SETPUF before VMASS should be rejected");
    const auto first_mass=life.commit_vmass(1,80,50,50,1,4,0);
    rejects([&]{life.commit_lid(1,first_mass.reflecting_lid_m,first_mass.puff_code);},
            "late lid before SETPUF should be rejected");
    inputs.step.puff_code=first_mass.puff_code;
    const auto updated=life.commit_sigma(1,inputs,yc,zc);
    const auto committed=life.state(1);
    require(committed.completed_substeps==1 &&
            committed.sigma_y_m==static_cast<float>(updated.adjust.stored_sigma_y_m) &&
            committed.sigma_z_m==static_cast<float>(updated.adjust.stored_sigma_z_m),
            "source-ported native sigma not preserved across substep");
    rejects([&]{(void)life.commit_sigma(1,inputs,yc,zc);},
            "stale caller overwrote native sigma history");
    require(life.state(1).completed_substeps==1,
            "failed sigma transition mutated state");
    // Original COMP L11391-11398: first lower reflecting lid, then a
    // higher lid on the following native, source-ported sigma substep.
    life.commit_lid(1,first_mass.reflecting_lid_m,first_mass.puff_code);
    const auto first_lid=life.state(1);
    require(first_lid.ziold_m==80.0F && first_lid.zimax_m==80.0F &&
            first_lid.committed_lid_steps==1,
            "CALPUFF COMP REAL4 max/last-lid commit differs");
    rejects([&]{life.commit_lid(1,80.0F,1);},
            "duplicate COMP lid commit accepted");
    rejects([&]{life.commit_lid(1,std::nanf(""),1);},
            "nonfinite original HLID accepted");
    const auto after=life.sample(1,met,static_met,0.5F,0.5F,50.0F);
    require(after.extent.z_top_m==static_cast<double>(50.0F+committed.sigma_z_m) &&
            after.extent.z_bottom_m==static_cast<double>(50.0F-committed.sigma_z_m),
            "next PUFFDZ step did not consume persisted native SIGZ");
    auto second_step=inputs;
    second_step.step.sigma_y_start_m=committed.sigma_y_m;
    second_step.step.sigma_z_start_m=committed.sigma_z_m;
    const auto second_mass=life.commit_vmass(1,150,50,50,committed.sigma_z_m,4,0);
    second_step.step.puff_code=second_mass.puff_code;
    (void)life.commit_sigma(1,second_step,yc,zc);
    life.commit_lid(1,second_mass.reflecting_lid_m,second_mass.puff_code);
    const auto second_lid=life.state(1);
    require(second_lid.ziold_m==150.0F &&
            second_lid.zimax_m==150.0F &&
            second_lid.committed_lid_steps==2,
            "CALPUFF lid increase not propagated through native state");
    rejects([&]{(void)life.sample(1,met,static_met,2.0F,0.5F,50.0F);},
            "out-of-grid native puff accepted");
    life.retire(1);
    require(life.active_count()==0,"retirement did not discard native state");
    rejects([&]{(void)life.state(1);},"retired puff still alive");
}
void local_native_vmass_integration() {
    using namespace cteas::puff;
    OriginalVerticalLifecycle native;
    NewPuffInputs point;
    point.source_x_km=0.5;
    point.source_y_km=0.5;
    point.effective_height_m=50.0;
    point.sigma_y_source_m=1.0;
    point.sigma_z_source_m=1.0;
    point.stability_class=4;
    InjectionInputs source;
    source.species_count=2;
    source.emission_duration_s=10.0;
    source.effective_height_m=50.0;
    source.max_layer_height_m=500.0;
    source.mixing_height_m=120.0;
    source.mass_fraction_mixed=1.0;
    source.stability_class=4;
    source.gaussian_distribution=1;
    source.emission_rate={2.0,1.0};
    native.admit_point(44,point,source);
    auto yc=[](double sigma,double dx,double dt)->SigmaCurvePoint {
        return {sigma>0?sigma:1.0+dt*0.1,dt,dx};
    };
    auto zc=[](double sigma,double dx,double dt,double)->SigmaCurvePoint {
        return {sigma>0?sigma:1.0+dt*0.05,dt,dx};
    };
    SigmaUpdateInputs step;
    step.step.puff_code=1;
    step.step.sigma_y_start_m=1;
    step.step.sigma_z_start_m=1;
    step.step.puff_height_m=50;
    step.step.mid_time_s=10;
    step.step.mid_distance_km=0.05;
    rejects([&]{(void)native.commit_sigma(44,step,yc,zc);},
            "SETPUF before VMASS should be rejected");
    // VMASS must use old SIGZB before SETPUF and retain pending late HLID.
    const auto vm=native.commit_vmass(44,80,50,50,1,4,0);
    require(native.state(44).vmass_pending &&
            native.state(44).completed_substeps==0,
            "VMASS not separate from SETPUF/history");
    rejects([&]{(void)native.commit_vmass(44,80,50,50,1,4,0);},
            "duplicate pre-SETPUF VMASS allowed");
    step.step.puff_code=vm.puff_code;
    (void)native.commit_sigma(44,step,yc,zc);
    rejects([&]{native.commit_lid(44,160,vm.puff_code);},
            "late lid allowed inconsistent VMASS HLID");
    native.commit_lid(44,vm.reflecting_lid_m,vm.puff_code);
    const auto after=native.state(44);
    require(vm.puff_code==1 && vm.reflecting_lid_m==80.0F &&
            after.ziold_m==80.0F && after.zimax_m==80.0F &&
            after.mass_mixed[0]==20.0F && after.mass_above[0]==0.0F &&
            after.committed_lid_steps==1,
            "native VMASS->COMP did not persist source mass / history");
    // A new VMASS is allowed only for the NEXT step; its rejection while
    // an earlier VMASS is pending was already asserted above.
    rejects([&]{
        (void)native.commit_lid(44,80,1);
    },"direct COMP lid path bypassed already-committed VMASS");
    step.step.sigma_y_start_m=after.sigma_y_m;
    step.step.sigma_z_start_m=after.sigma_z_m;
    const auto greater=native.commit_vmass(44,160,50,50,after.sigma_z_m,4,0);
    step.step.puff_code=greater.puff_code;
    (void)native.commit_sigma(44,step,yc,zc);
    native.commit_lid(44,greater.reflecting_lid_m,greater.puff_code);
    const auto persisted=native.state(44);
    require(greater.reflecting_lid_m==160.0F &&
            persisted.ziold_m==160.0F &&
            persisted.zimax_m==160.0F &&
            persisted.committed_lid_steps==2 &&
            persisted.completed_substeps==2,
            "native upper lid history not propagated across sigma substeps");
    native.retire(44);
    require(native.active_count()==0,"native VMASS retirement failed");
}
// Regression for CALPUFF COMP L10859 -> L10940: a falling PBL changes
// ICODE before SETPUF, and sigma MUST use the updated type, not old code.
void source_order_vmass_changes_code_before_sigma() {
    using namespace cteas::puff;
    OriginalVerticalLifecycle life;
    NewPuffInputs source;
    source.source_x_km=0.5;
    source.source_y_km=0.5;
    source.effective_height_m=50;
    source.sigma_y_source_m=1;
    source.sigma_z_source_m=1;
    source.stability_class=4;
    InjectionInputs emission;
    emission.species_count=1;
    emission.emission_duration_s=60;
    emission.effective_height_m=50;
    emission.mixing_height_m=120;
    emission.max_layer_height_m=200;
    emission.mass_fraction_mixed=1;
    emission.stability_class=4;
    emission.gaussian_distribution=1;
    emission.emission_rate={1.0};
    life.admit_point(19,source,emission);
    require(life.state(19).puff_code==1,"source code must start Gaussian=1");
    const auto mass=life.commit_vmass(19,20,50,50,1,4,0);
    require(mass.puff_code==5 && life.state(19).puff_code==5 &&
            life.state(19).completed_substeps==0 &&
            life.state(19).vmass_pending,
            "pre-SETPUF VMASS did not switch original ICODE 1 -> 5");
    SigmaUpdateInputs req;
    req.step.sigma_y_start_m=1;
    req.step.sigma_z_start_m=1;
    req.step.puff_height_m=50;
    req.step.mid_time_s=30;
    req.step.mid_distance_km=0.05;
    req.step.puff_code=1;
    auto yc=[](double s,double d,double t)->SigmaCurvePoint {
        return {s>0?s:1.0,t,d};
    };
    auto zc=[](double s,double d,double t,double)->SigmaCurvePoint {
        return {s>0?s:1.0,t,d};
    };
    rejects([&]{(void)life.commit_sigma(19,req,yc,zc);},
            "SETPUF accepted stale pre-VMASS ICODE 1");
    require(life.state(19).vmass_pending &&
            life.state(19).completed_substeps==0,
            "failed stale-code SETPUF corrupted pending VMASS");
    req.step.puff_code=mass.puff_code;
    (void)life.commit_sigma(19,req,yc,zc);
    require(life.state(19).completed_substeps==1 &&
            life.state(19).committed_lid_steps==0 &&
            life.state(19).vmass_pending,
            "SETPUF committed historical lid before original sampling point");
    life.commit_lid(19,mass.reflecting_lid_m,mass.puff_code);
    require(life.state(19).puff_code==5 &&
            life.state(19).ziold_m==120.0F &&
            life.state(19).completed_substeps==1 &&
            life.state(19).committed_lid_steps==1 &&
            !life.state(19).vmass_pending,
            "late source-order ICODE/ZIOLD history incorrectly committed");
}
void original_high_uniform_layer() {
    using namespace cteas::puff;
    OriginalVerticalLifecycle vertical;
    NewPuffInputs p;
    p.source_x_km=0.5;
    p.source_y_km=0.5;
    p.effective_height_m=150.0;
    p.sigma_y_source_m=1.0;
    p.sigma_z_source_m=1.0;
    p.stability_class=4;
    InjectionInputs injection;
    injection.species_count=1;
    injection.emission_duration_s=60.0;
    injection.effective_height_m=150.0;
    injection.mixing_height_m=120.0;
    injection.max_layer_height_m=200.0;
    injection.mass_fraction_mixed=0.0;
    injection.stability_class=4;
    injection.gaussian_distribution=0;
    injection.emission_rate={1.0};
    vertical.admit_point(13,p,injection);
    require(vertical.state(13).puff_code==4 &&
            vertical.state(13).mass_above.at(0)==60.0F,
            "original high-release uniform ICODE=4 setup invalid");
    OriginalMetHour met;
    met.nx=2;met.ny=2;met.nz=2;
    met.zi.assign(4,120.0F);met.ipgt.assign(4,4);
    met.u.assign(8,1.0F);met.v.assign(8,2.0F);
    for(std::size_t idx=4;idx<8;idx++) {
        met.u[idx]=3.0F;met.v[idx]=4.0F;
    }
    Calmet21Static static_met;
    static_met.cell_face_m={0.0F,100.0F,200.0F};
    const auto v=vertical.sample(13,met,static_met,
                                 0.5F,0.5F,150.0F);
    require(v.extent.z_bottom_m==100.0 && v.extent.z_top_m==200.0 &&
            v.wind.u_ms==3.0 && v.wind.v_ms==4.0,
            "native ICODE4 failed to use original ZFACE level and upper U/V");
    require(vertical.state(13).completed_substeps==0,
            "high uniform vertical sampling mutated source");
}
void original_first_step(const char* met_path,const char* dgm_path) {
    using namespace cteas::puff;
    std::ifstream file(dgm_path,std::ios::binary);
    require(bool(file),"frozen first-hour DGM missing");
    DgmRecord row{};
    require(bool(file.read(reinterpret_cast<char*>(&row),sizeof(row))),
            "missing initial original DGM record");
    require(row.i[0]==1 && row.i[1]==202200100 && row.i[3]==1 &&
            row.i[4]==1,"frozen original initial point puff changed");
    int observed=0;
    const auto parsed=OriginalMetHourlyReader::read(
        met_path,[&](const Calmet21Header&,const Calmet21Static& static_met,
                      const OriginalMetHour& hour) {
            if(hour.begin.year!=2022 || hour.begin.julian_day!=1 ||
               hour.begin.hour!=0)return;
            const auto cell=original_met_cell(row.f[0],row.f[1],hour.nx,hour.ny);
            require(cell.ix_1based==row.i[5] &&
                    cell.iy_1based==row.i[6] &&
                    hour.ipgt.at(cell.offset_0based)==row.i[8] &&
                    hour.zi.at(cell.offset_0based)==row.f[3],
                    "native first-hour MET data not the original puff cell");
            NewPuffInputs point;
            point.source_x_km=row.f[0];point.source_y_km=row.f[1];
            point.effective_height_m=row.f[6]; // original HTMET, not guessed
            point.sigma_y_source_m=1.0F;
            point.sigma_z_source_m=1.0F;
            point.stability_class=row.i[8];
            InjectionInputs injection;
            injection.species_count=1;injection.emission_duration_s=60;
            injection.effective_height_m=point.effective_height_m;
            injection.mixing_height_m=hour.zi[cell.offset_0based];
            injection.max_layer_height_m=static_met.cell_face_m.back();
            injection.mass_fraction_mixed=1.0;
            injection.stability_class=point.stability_class;
            injection.gaussian_distribution=1;
            injection.emission_rate={1.0};
            OriginalVerticalLifecycle native;
            native.admit_point(1,point,injection);
            const auto calculated=native.sample(
                1,hour,static_met,row.f[0],row.f[1],row.f[6]);
            require(calculated.extent.z_top_m==row.f[7] &&
                    calculated.extent.z_bottom_m==row.f[8] &&
                    static_cast<float>(calculated.wind.u_ms)==row.f[9] &&
                    static_cast<float>(calculated.wind.v_ms)==row.f[10],
                    "native release -> PUFFDZ -> ADVECT initial step not exact");
            ++observed;
        },true);
    require(parsed.intervals==143 && observed==1,
            "first original complete hour not sampled");
}
} // namespace

int main(int argc,char** argv) {
    try {
        local_native_state();
        original_high_uniform_layer();
        local_native_vmass_integration();
        source_order_vmass_changes_code_before_sigma();
        if(argc==3) original_first_step(argv[1],argv[2]);
        else if(argc!=1)throw std::invalid_argument("usage: native-vertical-test [MET DGM]");
        std::cout<<"P7_NATIVE_VERTICAL_PERSISTENT=PASS"
                 <<" RELEASE_INJECT=REAL4 PUFFDZ_ADVECT=NATIVE"
                 <<" SIGMA_UPDATE=NATIVE"
                 <<" COMP_LAST_LID_COMMIT=NATIVE_REAL4"
                 <<" VMASS_REAL4_NATIVE_STATE=PERSISTED"
                 <<" VMASS_ORIGINAL_143H_INTEGRATION=NOT_YET_VALIDATED"
                 <<" FIRST_ORIGINAL_STEP="<<(argc==3?"EXACT":"NOT_TESTED")<<"\n";
        return 0;
    } catch(const std::exception& e) {
        std::cerr<<"P7_NATIVE_VERTICAL_PERSISTENT=FAIL "<<e.what()<<"\n";
        return 1;
    }
}
