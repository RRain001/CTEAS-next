#include "cteas/p6/terrain_envelope.hpp"
#include <cmath>
#include <exception>
#include <functional>
#include <iostream>
#include <stdexcept>
#include <vector>
namespace p = cteas::calmet::p6;
void check(bool ok,const char* why){if(!ok)throw std::runtime_error(why);}
void fails(const std::function<void()>& fn){bool failed=false;try{fn();}catch(const std::invalid_argument&){failed=true;}check(failed,"invalid TERSET input passed");}
int main(){
    try{
        std::vector<float> h(2500,63.0f);
        auto flat=p::terset(h,50,50,100,100,15);
        for(std::size_t n=0;n<h.size();++n){
            check(flat.maximum_m[n]==63.0f&&flat.minimum_m[n]==63.0f,"flat topography extrema");
            check(flat.distance_to_maximum_m[n]==0.0f&&flat.distance_to_minimum_m[n]==0.0f,
                  "flat topography distance initial sentinel must remain zero");
        }
        // TERRAD=15km spans entire 5km box, including corners. This case tests
        // real study mode and original CALMET's finite-grid truncation.
        h[0]=1000;
        h.back()=-50;
        const auto wide=p::terset(h,50,50,100,100,15);
        for(std::size_t n=0;n<h.size();++n)
            check(wide.maximum_m[n]==1000&&wide.minimum_m[n]==-50,
                  "large TERRAD must span entire study domain");
        check(wide.distance_to_maximum_m[0]==0.0f,"exact maximum distance");
        check(wide.distance_to_minimum_m.back()==0.0f,"exact minimum distance");
        // A local search must *exclude* distant extrema, including corners.
        const auto near=p::terset(h,50,50,100,100,0.12f);
        check(near.maximum_m.back()==63.0f,"radius inclusion beyond boundary");
        check(near.minimum_m[0]==63.0f,"radius exclusion beyond boundary");
        check(near.maximum_m[0]==1000.0f&&near.minimum_m.back()==-50.0f,
              "same cell extremum");
        // A nearest local neighbor should be captured at precisely 100m.
        check(near.maximum_m[1]==1000.0f&&near.minimum_m[1]==63.0f,
              "local radius one-neighbor highest elevation");
        check(std::abs(near.distance_to_maximum_m[1]-100.0f)<1.e-4f,
              "nearest grid peak distance");
        fails([&]{(void)p::terset(h,50,50,0,100,15);});
        fails([&]{(void)p::terset(h,50,50,100,100,-1);});
        fails([&]{(void)p::terset(h,400,400,100,100,15);});
        h[300]=std::numeric_limits<float>::quiet_NaN();
        fails([&]{(void)p::terset(h,50,50,100,100,15);});
        std::cout<<"PASS P6C_TERSET_SOFTWARE_ONLY (Fortran parity separate)\n";
        return 0;
    }catch(const std::exception& ex){
        std::cerr<<"FAIL: "<<ex.what()<<'\n';
        return 1;
    }
}
