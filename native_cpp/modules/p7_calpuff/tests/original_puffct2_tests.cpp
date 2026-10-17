#include "cteas/puff/original_puffct2.hpp"
#include <bit>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <limits>
#include <stdexcept>

using namespace cteas::puff;
static void require(bool ok,const char* what){
    if(!ok)throw std::runtime_error(what);
}
int main() {
    try {
        OriginalPuffct2Step s;
        s.x_begin_m=100.0F;s.y_begin_m=200.0F;s.z_begin_m=50.0F;
        s.x_end_m=200.0F;s.y_end_m=300.0F;s.z_end_m=20.0F;
        s.terrain_fraction=0.4F;s.upslope=true;
        const auto a=original_puffct2(s,0.2F);
        const auto end=original_puffct2(s,0.8F);
        require(a.x_m==120.0F && a.y_m==220.0F &&
                a.z_m==35.0F && end.z_m==20.0F,
                "uphill fractional fall/plateau changed");
        s.upslope=false;
        const auto pre=original_puffct2(s,0.2F);
        const auto post=original_puffct2(s,0.7F);
        require(pre.z_m==50.0F &&
                std::abs(post.z_m-35.0F)<1.e-5F,
                "downhill delayed height transition changed");
        s.upslope=true;s.terrain_fraction=0.0F;
        require(original_puffct2(s,0.5F).z_m==50.0F,
                "upslope no terrain response must retain initial height");
        s.upslope=false;s.terrain_fraction=1.0F;
        require(original_puffct2(s,0.5F).z_m==50.0F,
                "downslope no terrain response must retain initial height");
        s.upslope=true;s.terrain_fraction=0.4F;
        const auto once=original_puffct2(s,-0.3F);
        const auto twice=original_puffct2(s,-0.3F);
        require(std::bit_cast<std::uint32_t>(once.z_m)==
                std::bit_cast<std::uint32_t>(twice.z_m),
                "FRAC extrapolation must preserve bitwise determinism");
        // MCTADJ=2 original PUFRECS terrain/rise/pole branch with
        // explicit synthetic ground and relief data (unit fixture only).
        const auto position=original_puffct2({
            .x_begin_m=100,.y_begin_m=200,.z_begin_m=50,
            .x_end_m=200,.y_end_m=300,.z_end_m=20,
            .terrain_fraction=0.4F,.upslope=true
        },0.2F);
        const auto elevated=original_mctadj2_receptor_height(
            position,60.0F,120.0F,{
                .receptor_ground_elevation_msl=330,
                .terrain_peak_elevation_msl=350,
                .terrain_under_puff_msl=320,
                .brunt_vaisala_s=0.2F,
                .wind_speed_ms=2.0F,.receptor_height_m=0.0F
            });
        require(std::abs(elevated.puff_height_above_ground_m-17.5F)<1.e-5F &&
                elevated.pole_height_m==10.0F,
                "PUFRECS MCTADJ2 gradual-rise/pole branch drift");
        const auto neutral=original_mctadj2_receptor_height(
            position,60.0F,120.0F,{
                .receptor_ground_elevation_msl=330,
                .terrain_peak_elevation_msl=350,
                .terrain_under_puff_msl=320,
                .brunt_vaisala_s=0.0F,
                .wind_speed_ms=2.0F,.receptor_height_m=1.5F
            });
        require(neutral.pole_height_m==1.5F,
                "PUFRECS MCTADJ2 BVF=0 receptor pole changed");
        bool refused=false;
        s.terrain_fraction=std::numeric_limits<float>::quiet_NaN();
        try{(void)original_puffct2(s,0.5F);}
        catch(const std::invalid_argument&){refused=true;}
        require(refused,"PUFFCT2 silently accepted missing/NaN CTADJ2 fraction");
        std::cout<<"P7_ORIGINAL_PUFFCT2_NATIVE_UNIT=PASS"
                 <<" UPSLOPE_DOWNSLOPE=YES FRAC_EXTRAPOLATE=YES"
                 <<" FINITE_STATE_REQUIRED=YES NO_ORACLE_INPUT=YES\n";
        return 0;
    }catch(const std::exception& e){
        std::cerr<<"P7_ORIGINAL_PUFFCT2_NATIVE_UNIT=FAIL "<<e.what()<<"\n";
        return 1;
    }
}
