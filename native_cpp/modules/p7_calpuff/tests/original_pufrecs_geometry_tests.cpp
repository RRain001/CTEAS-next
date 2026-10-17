#include "cteas/puff/original_pufrecs_geometry.hpp"
#include <cmath>
#include <iostream>
#include <stdexcept>

using namespace cteas::puff;
static void check(bool ok,const char* what){
    if(!ok)throw std::runtime_error(what);
}
int main(){
    try{
        auto a=original_slgfrac(50,1,100,0,0,0);
        check(a.along_m==50 && a.across_m==1 &&
              a.fraction==0.5F && a.projected_length_m==100.0F,
              "original SLGFRAC along/cross/fraction mapping");
        auto small=original_slgfrac(0.5F,0.5F,0.5F,0,0,0);
        check(small.fraction==0 && small.projected_length_m==1 &&
              small.inverse_length_per_m==1,
              "vendor projected-length<1m branch changed");
        auto base=original_pufrecs_geometry({
            .x_receptor_m=200,.x_begin_m=0,.x_end_m=100,
            .sigma_y_begin_m=10,.sigma_y_end_m=20,.fclip=1,
            .travel_distance_begin_m=100,.mean_wind_ms=2,.clip=false});
        check(base.fraction==2 && base.along_m==200 &&
              base.distance_to_receptor_m==300 &&
              base.time_to_receptor_s==150,
              "original PUFRECS must extrapolate when LCLIP false");
        auto clip=original_pufrecs_geometry({
            .x_receptor_m=200,.x_begin_m=0,.x_end_m=100,
            .sigma_y_begin_m=10,.sigma_y_end_m=20,.fclip=1,
            .travel_distance_begin_m=100,.mean_wind_ms=2,.clip=true});
        check(std::abs(clip.fraction-1.2F)<1.0e-6F &&
              std::abs(clip.along_m-120.0F)<1.0e-4F &&
              std::abs(clip.time_to_receptor_s-110.0F)<1.0e-4F && clip.clipped,
              "original PUFRECS FCLIP extension failed");
        auto upstream=original_pufrecs_geometry({
            .x_receptor_m=-500,.x_begin_m=0,.x_end_m=100,
            .sigma_y_begin_m=10,.sigma_y_end_m=20,.fclip=1,
            .travel_distance_begin_m=30,.mean_wind_ms=3,.clip=false});
        check(upstream.distance_to_receptor_m==0 &&
              upstream.time_to_receptor_s==0 &&
              std::abs(upstream.fraction+0.3F)<1.0e-6F,
              "original PUFRECS source-boundary reset failed");
        OriginalPufrecsGridStepInputs step;
        step.x_begin_cells=5.0F; step.y_begin_cells=5.5F;
        step.x_end_cells=6.0F; step.y_end_cells=5.5F;
        step.sigma_y_begin_m=20.0F;
        step.sigma_y_end_m=30.0F;
        step.distance_begin_m=200.0F; step.mean_wind_ms=2.0F;
        step.met_spacing_m=100.0F;
        step.ibsamp=1; step.jbsamp=1;
        step.sampling_nx=50; step.sampling_ny=50;
        step.fclip=3.0F; step.clip=false;
        // Sampling-grid (i=5,j=5) has receptor CENTER (5.5,5.5)
        // in the MET-cell frame; native puff goes (5,5.5)->(6,5.5).
        const auto mapped=original_pufrecs_grid_receptor_geometry(step,5+5*50);
        const auto direct=original_pufrecs_geometry({
            .x_receptor_m=550.0F,.y_receptor_m=550.0F,
            .x_begin_m=500.0F,.y_begin_m=550.0F,
            .x_end_m=600.0F,.y_end_m=550.0F,
            .sigma_y_begin_m=20.0F,.sigma_y_end_m=30.0F,
            .fclip=3.0F,.travel_distance_begin_m=200.0F,
            .mean_wind_ms=2.0F,.clip=false
        });
        check(mapped.fraction==0.5F && mapped.along_m==50.0F &&
              mapped.distance_to_receptor_m==250.0F &&
              mapped.time_to_receptor_s==125.0F &&
              mapped.fraction==direct.fraction &&
              mapped.along_m==direct.along_m &&
              mapped.distance_to_receptor_m==direct.distance_to_receptor_m &&
              mapped.time_to_receptor_s==direct.time_to_receptor_s &&
              mapped.clipped==direct.clipped,
              "MET-grid cell to receiver center off by half a grid cell");
        bool rejected_index=false;
        try{(void)original_pufrecs_grid_receptor_geometry(step,2500);}
        catch(const std::out_of_range&){rejected_index=true;}
        check(rejected_index,"PUFRECS grid bridge accepted outside receptor");
        auto bad_step=step; bad_step.met_spacing_m=0.0F;
        bool rejected_spacing=false;
        try{(void)original_pufrecs_grid_receptor_geometry(bad_step,0);}
        catch(const std::invalid_argument&){rejected_spacing=true;}
        check(rejected_spacing,"PUFRECS grid bridge accepted zero MET spacing");
        std::cout<<"P7_PUFRECS_NATIVE_GRID_RECEIVER_FRAME=PASS"
                 <<" GRID_CENTER_HALF_CELL=YES"
                 <<" REAL4=YES SOURCE_PORTED_GEOMETRY=YES"
                 <<" RECEPTOR_SIGTY_SIGTZ_GRISE=OPEN\\n";
        bool rejected=false;
        try{(void)original_pufrecs_geometry({.mean_wind_ms=0});}
        catch(const std::invalid_argument&){rejected=true;}
        check(rejected,"PUFRECS accepted calm UAVG without original calm branch");
        std::cout<<"P7_ORIGINAL_PUFRECS_GEOMETRY=PASS SLGFRAC=REAL4"
                 <<" FCLIP=YES UPWIND_SOURCE=YES"
                 <<" FULL_PUFRECS_SIGMA_GRISE_TERRAIN=OPEN\\n";
        return 0;
    }catch(const std::exception& e){
        std::cerr<<"P7_ORIGINAL_PUFRECS_GEOMETRY=FAIL "<<e.what()<<"\n";
        return 1;
    }
}
