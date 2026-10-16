#include "cteas/puff/original_native_terrain.hpp"
#include <cmath>
#include <iostream>
#include <stdexcept>

using namespace cteas::puff;
static void need(bool ok,const char* reason){
    if(!ok)throw std::runtime_error(reason);
}
int main(){
    try{
        Calmet21Static statics;
        constexpr int nx=12,ny=12;
        statics.present=true;
        statics.elevation_m.resize(nx*ny);
        for(int j=0;j<ny;++j)for(int i=0;i<nx;++i)
            statics.elevation_m[static_cast<std::size_t>(j*nx+i)]=
                40.0F+0.3F*static_cast<float>(i)+
                0.1F*static_cast<float>(j);
        const auto terrain=OriginalNativeTerrain::from_calmet(
            statics,nx,ny,100.0F);
        const auto lookup=terrain.constraint_lookup();
        need(lookup.cell_elevation_msl(5.2,6.1)>40 &&
             std::isfinite(lookup.elevation_msl(5.2,6.1)) &&
             std::isfinite(lookup.relief(5.2,6.1,5)) &&
             lookup.valley_width(5.2,6.1,1)>=-1,
             "original TRELIEF/VWIDTH/GETELEV native source cache incomplete");
        // Original CALPUFF GETCELL/GRIDIJ (unlike a strict grid accessor)
        // clamps the last step of a departing puff to its boundary MET
        // cell. Its independent GETELEV bilinear interpolation remains
        // a different, source-defined operation.
        need(lookup.cell_elevation_msl(-0.2,6.1)==
                 statics.elevation_m[6*nx] &&
             lookup.cell_elevation_msl(12.3,6.1)==
                 statics.elevation_m[6*nx+(nx-1)] &&
             lookup.relief(-0.2,6.1,5)==lookup.relief(0.0,6.1,5) &&
             lookup.valley_width(12.3,6.1,1)==
                 lookup.valley_width(11.3,6.1,1),
             "source GETCELL did not clamp out-of-domain final puff substep");
        const OriginalPuffct2Result position{
            .x_m=520.0F,.y_m=610.0F,.z_m=30.0F};
        const auto receiver=terrain.receptor(
            5+6*nx,1,1,nx,ny,position,0.015F,1.2F);
        const auto expected=statics.elevation_m[5+6*nx];
        need(receiver.receptor_ground_elevation_msl==expected &&
             receiver.terrain_peak_elevation_msl>=expected &&
             std::isfinite(receiver.terrain_under_puff_msl),
             "PUFRECS ground/peak/puff GETELEV indices mismatched");
        // PUFRECS L5341-L5343 computes XR1*DGRIDI in REAL4, not XR1/DGRID.
        // A steep synthetic stencil makes the 1-ULP coordinate difference
        // observable through GETELEV, so the old divide path fails this test.
        Calmet21Static steep=statics;
        for(int j=0;j<ny;++j)for(int i=0;i<nx;++i)
            steep.elevation_m[static_cast<std::size_t>(j*nx+i)]=
                100.0F+100000.0F*static_cast<float>(i%2)+
                25.0F*static_cast<float>(j);
        const auto steep_terrain=OriginalNativeTerrain::from_calmet(
            steep,nx,ny,100.0F);
        const auto steep_lookup=steep_terrain.constraint_lookup();
        const float recip=1.0F/100.0F;
        const OriginalPuffct2Result witness{
            .x_m=603.47F,.y_m=745.678F,.z_m=30.0F};
        const float xm=witness.x_m*recip,ym=witness.y_m*recip;
        const float xd=witness.x_m/100.0F,yd=witness.y_m/100.0F;
        need(xm!=xd || ym!=yd,
             "REAL4 reciprocal-multiply witness accidentally equals divide");
        const float exact=static_cast<float>(steep_lookup.elevation_msl(
            static_cast<double>(xm),static_cast<double>(ym)));
        const float legacy=static_cast<float>(steep_lookup.elevation_msl(
            static_cast<double>(xd),static_cast<double>(yd)));
        need(exact!=legacy,
             "steep GETELEV witness does not distinguish REAL4 order");
        const auto strict=steep_terrain.receptor(
            5+6*nx,1,1,nx,ny,witness,0.015F,1.2F);
        need(strict.terrain_under_puff_msl==exact,
             "PUFRECS GETELEV must use precomputed REAL4 DGRIDI");

        bool missed=false;
        try {(void)terrain.receptor(nx*ny,1,1,nx,ny,position,0.0F,1.2F);}
        catch(const std::invalid_argument&){missed=true;}
        need(missed,"terrain adapter allowed an invalid receptor index");
        statics.elevation_m.clear();
        bool no_grid=false;
        try{(void)OriginalNativeTerrain::from_calmet(statics,nx,ny,100.0F);}
        catch(const std::invalid_argument&){no_grid=true;}
        need(no_grid,"terrain adapter invented missing CALMET static ELEV");
        std::cout<<"P7_REAL_CALMET_STATIC_TERRAIN_ADAPTER=PASS"
                 <<" TRELIEF=SOURCE_PORTED GETELEV=SOURCE_PORTED"
                 <<" VWIDTH=SOURCE_PORTED"
                 <<" NO_DGM=YES MCTADJ2_ORIGINAL_CONC=NOT_YET_ACCEPTED\\n";
        return 0;
    }catch(const std::exception& e){
        std::cerr<<"P7_REAL_CALMET_STATIC_TERRAIN_ADAPTER=FAIL "
                 <<e.what()<<"\\n";
        return 1;
    }
}
