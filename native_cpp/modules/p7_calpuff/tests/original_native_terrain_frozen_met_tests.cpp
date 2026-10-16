// Ground the native MCTADJ2 TRELIEF/GETELEV grid in the actual locked
// Hefei CALMET.DAT OUTHD 2-D ELEV, never in synthetic cells or a DGM
// source oracle. This is an INPUT provenance/integration gate, not
// full CALPUFF 1h receptor numerical parity.
#include "cteas/puff/calmet21.hpp"
#include "cteas/puff/original_native_terrain.hpp"
#include <algorithm>
#include <bit>
#include <cstdint>
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <string>

using namespace cteas::puff;
static void check(bool b,const char* why){
    if(!b)throw std::runtime_error(why);
}
int main(int argc,char** argv){
    try{
        if(argc!=2)throw std::invalid_argument("usage: p7_frozen_terrain MET.DAT");
        const auto met=Calmet21Reader::read(argv[1],{},true);
        check(met.header.nx==50 && met.header.ny==50 &&
              met.header.nz==9 && met.header.dx_m==100.0F,
              "frozen Hefei grid/header mismatch");
        const auto& static_grid=met.statics;
        check(static_grid.present && static_grid.elevation_m.size()==2500,
              "locked MET.DAT missing 2500 original ELEV records");
        const auto bounds=std::minmax_element(
            static_grid.elevation_m.begin(),static_grid.elevation_m.end());
        check(*bounds.first==25.0F && *bounds.second==59.5F,
              "locked Hefei CALMET ELEV range not the accepted source");
        const auto terrain=OriginalNativeTerrain::from_calmet(
            static_grid,met.header.nx,met.header.ny,met.header.dx_m);
        const auto lookup=terrain.constraint_lookup();
        const double x=25.5,y=25.5;
        const double elev=lookup.elevation_msl(x,y);
        const double relief=lookup.relief(x,y,5);
        const int width=lookup.valley_width(x,y,1);
        check(std::isfinite(elev)&&std::isfinite(relief)&&
              width>=-1&&relief>=*bounds.first,
              "actual CALMET terrain lookup returned missing/invalid data");
        const OriginalPuffct2Result sample{
            .x_m=2550.0F,.y_m=2550.0F,.z_m=30.0F};
        const auto rec=terrain.receptor(
            25U+25U*50U,1,1,50,50,sample,0.015F,1.2F);
        check(std::isfinite(rec.terrain_under_puff_msl) &&
              std::isfinite(rec.terrain_peak_elevation_msl) &&
              rec.terrain_peak_elevation_msl>=
                  rec.receptor_ground_elevation_msl &&
              rec.receptor_ground_elevation_msl==
                  static_grid.elevation_m[25U+25U*50U],
              "frozen original MET receiver ground / relief mapping drift");
        // REAL4 provenance at PUFRECS interface, without converting
        // source field through a lower-precision synthetic approximation.
        check(std::bit_cast<std::uint32_t>(
            rec.receptor_ground_elevation_msl)==
            std::bit_cast<std::uint32_t>(
                static_grid.elevation_m[25U+25U*50U]),
            "locked CALMET ELEV lost float32 bits in native PUFRECS bridge");
        std::cout<<"P7_HEFEI_FROZEN_MET_MCTADJ2_TERRAIN_INPUT=PASS"
                 <<" GRID=50X50X9 DELSAM_M=100"
                 <<" ELEV_MIN_M="<<*bounds.first
                 <<" ELEV_MAX_M="<<*bounds.second
                 <<" REAL4_CELL_ELEV=BITWISE"
                 <<" TRELIEF_GETELEV_VWIDTH=SOURCE_PORTED"
                 <<" DGM_DRIVING_INPUT=NO"
                 <<" CALCPF_1H_REAL_PARITY=NOT_YET_ACCEPTED\\n";
        return 0;
    }catch(const std::exception& e){
        std::cerr<<"P7_HEFEI_FROZEN_MET_MCTADJ2_TERRAIN_INPUT=FAIL "
                 <<e.what()<<"\\n";return 1;
    }
}
