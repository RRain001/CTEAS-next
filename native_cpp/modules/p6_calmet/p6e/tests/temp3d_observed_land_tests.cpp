#include "cteas/p6e/temp3d_observed_land.hpp"
#include <cassert>
#include <cmath>
#include <stdexcept>
using namespace cteas::p6e;
template<class F>void bad(F f){bool yes=false;try{f();}catch(const std::invalid_argument&){yes=true;}assert(yes);}
int main(){
    Temp3dObservedInput a;
    a.nx=2;a.ny=1;a.nz=4;a.justa={1,-1};
    a.station_x_m={50.f,150.f};a.station_y_m={50.f,50.f};
    a.face_z_m={0.f,100.f,250.f,500.f,1000.f};
    a.aa_face_temp_k={300.f,299.f,298.f,297.f,295.f,
                       300.f,298.f,297.f,295.f,291.f};
    a.bb_face_temp_k={301.f,300.f,299.f,298.f,297.f,
                       301.f,299.f,298.f,296.f,292.f};
    a.surface_temp_k={300.f,295.f};
    a.convective_zi_m={0.f,500.f};
    auto z=temp3d_observed_land(a);
    assert(z.size()==8&&z[0]==300.f&&z[1]==295.f);
    assert(z[2]<300.f&&z[3]<295.f);
    a.irad=2;
    assert(temp3d_observed_land(a).size()==8);
    a.current_hour_utc=13;bad([&]{return temp3d_observed_land(a);});
    a.current_hour_utc=6;a.face_z_m[2]=a.face_z_m[1];
    bad([&]{return temp3d_observed_land(a);});
}
