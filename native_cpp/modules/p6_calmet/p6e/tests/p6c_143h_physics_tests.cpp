// E16: 143 sequential synthetic one-cell physics steps, on real P6C
// source-typed hourly COMP/RDSN state with 12-hour AA/BB turnover.
// This is a SOFTWARE temporal integration gate, not original full
// 2022 CALMET/COMP meteorology or original field numerical parity.
#include "cteas/p6e/p6c_hourly_bridge.hpp"
#include "cteas/p6e/temp3d_observed_land.hpp"
#include <cassert>
#include <chrono>
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <vector>

using namespace cteas::calmet::p6;
using namespace cteas::p6e;
int main() {
    using namespace std::chrono;
    const auto start=sys_days{year{2022}/January/1};
    Upper2022 upper;upper.station_id=58424;
    std::vector<std::vector<LayerWind>> layers;
    std::vector<std::vector<float>> faces;
    // P6C buffer has 13 instantaneous observations for 143h.
    const std::vector<float> zface{0.f,50.f,150.f,300.f,550.f,900.f};
    for(int n=0;n<=12;++n) {
        UpperSounding s;
        s.station_id=58424;
        s.start=sys_seconds{start}+hours{12*n};
        s.end=s.start;
        for(float z:{0.f,150.f,450.f,800.f,1400.f,2200.f}) {
            UpperLevel lev;
            lev.height_lgl_m=z;
            lev.temperature_k=303.f-0.007f*z+0.25f*n;
            lev.height_valid=true;lev.temperature_valid=true;
            s.data.push_back(lev);
        }
        upper.soundings.push_back(s);
        layers.push_back(std::vector<LayerWind>(5,LayerWind{2.f,1.f}));
        std::vector<float> t;
        for(float z:zface)t.push_back(301.f-0.007f*z+0.25f*n);
        faces.push_back(t);
    }
    Surface2022 surface;surface.station_id=999;
    for(int n=0;n<143;++n) {
        SurfaceInterval s;
        s.start=sys_seconds{start}+hours{n};s.end=s.start+hours{1};
        s.obs.temperature_k=293.f+static_cast<float>(n%6);
        s.obs.temperature_valid=true;
        s.obs.humidity_pct=55+n%20;s.obs.humidity_valid=true;
        s.obs.opaque_cloud_tenths=4;s.obs.cloud_valid=true;
        s.obs.precip_code=9999;s.obs.precipitation_code_valid=false;
        surface.hourly.push_back(s);
    }
    CompBufferedTimeline comp(upper,layers,faces);
    RdsnBufferedTimeline rdsn(surface);
    float previous_convective_height=60.f,previous_dptt=0.2f;
    int daytime=0,stable=0,neutral=0,aa_swapped=0,complete=0;
    double temperature_checksum=0.,height_checksum=0.;
    for(int n=1;n<=143;++n) {
        const auto end=sys_seconds{start}+hours{n};
        const auto comp_hour=comp.hour(end);
        const auto surface_hour=rdsn.select(end-hours{1},end);
        const auto h=p6c_observed_hour(upper,comp_hour,surface_hour);
        assert(h.end==end&&h.precipitation_code==9999);
        assert(!h.precipitation_code_observed);
        if(h.justa<0)++aa_swapped;
        if(h.past_seconds%3600!=0||h.gap_seconds!=43200)
            throw std::runtime_error("E16 sounding interpolation clock corrupted");
        // One land receptor with strictly supplied independent physical
        // state; do not infer a gridded wind or QH from P6C station T.
        MixhtObservedMcInput mix;
        mix.nx=1;mix.ny=1;mix.zimax=700.f;mix.dzzi=100.f;
        mix.izicrlx=1;
        mix.landuse={12};mix.nearu={1};
        const float qh=(n%4==0)?-0.1f:((n%5==0)?0.f:125.f);
        if(qh<0.f)++stable;
        else if(qh==0.f)++neutral;
        else ++daytime;
        mix.qh={qh};mix.ustar={0.3f};mix.el={70.f};
        mix.rho={1.2f};mix.cmech={100.f};mix.fcori={7e-5f};
        mix.initial_zi={0.f};
        mix.initial_ziconv={previous_convective_height};
        mix.initial_dptt={previous_dptt};
        apply_p6c_hour_to_mixht_one_station(mix,h);
        assert(mix.justa.size()==1&&mix.justa.front()==h.justa);
        const auto heights=mixht_observed_mc(mix);
        const float zi=heights.zi.at(0), conv=heights.ziconv.at(0);
        if(!std::isfinite(zi)||!std::isfinite(conv)||
           zi<mix.zimin||zi>mix.zimax||conv<0.f||conv>mix.zimax)
            throw std::runtime_error("E16 nonphysical sequential mixing height");
        if(qh<0.f && (conv!=0.f||heights.dptt[0]!=0.f))
            throw std::runtime_error("E16 stable path did not reset convective memory");
        previous_convective_height=conv;
        previous_dptt=heights.dptt[0];
        Temp3dObservedInput temp;
        temp.nx=1;temp.ny=1;temp.nz=5;
        temp.face_z_m=zface;
        temp.dgrid_m=100.f;temp.irad=1;
        // Date-independent offset WITHIN the original sounding bracket,
        // not the absolute UTC hour (13h must map to 1h after 12Z).
        temp.current_hour_utc=h.past_seconds/3600;
        temp.justa={h.justa};temp.station_x_m={50.f};
        temp.station_y_m={50.f};
        temp.aa_face_temp_k=h.physical_aa_face_t_k;
        temp.bb_face_temp_k=h.physical_bb_face_t_k;
        temp.surface_temp_k={h.surface_temp_k};
        temp.convective_zi_m={conv};
        const auto profile=temp3d_observed_land(temp);
        if(profile.size()!=5||profile[0]!=h.surface_temp_k)
            throw std::runtime_error("E16 TEMP3D did not preserve observed surface temperature");
        for(float t:profile) {
            if(!std::isfinite(t)||t<180.f||t>350.f)
                throw std::runtime_error("E16 nonphysical 3D temperature field");
            temperature_checksum+=t;
        }
        height_checksum+=zi;
        ++complete;
    }
    assert(complete==143&&daytime>30&&stable>20&&neutral>15);
    assert(aa_swapped>50);
    assert(std::isfinite(temperature_checksum) &&
           std::isfinite(height_checksum) && height_checksum>1000.);
    std::cout<<"PASS_P6E_E16_SYNTHETIC_143H_MIXHT_TEMP3D "
             <<"hours="<<complete<<" positive_QH="<<daytime
             <<" stable_QH="<<stable<<" neutral_QH="<<neutral
             <<" swapped_AABB="<<aa_swapped
             <<" temp_checksum="<<temperature_checksum
             <<" height_checksum="<<height_checksum
             <<" ORIGINAL_2022_FULL_CASE_PARITY=NOT_VERIFIED\n";
}
