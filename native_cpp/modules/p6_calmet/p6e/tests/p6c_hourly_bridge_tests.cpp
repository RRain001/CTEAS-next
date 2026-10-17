#include "cteas/p6e/p6c_hourly_bridge.hpp"
#include <cassert>
#include <chrono>
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <vector>
using namespace cteas::calmet::p6;
using namespace cteas::p6e;
int main(){
    using namespace std::chrono;
    const auto start=sys_days{year{2022}/January/1};
    Upper2022 upper;
    std::vector<std::vector<LayerWind>> layers;
    std::vector<std::vector<float>> faces;
    for(int n=0;n<=12;++n){
        UpperSounding s;
        s.station_id=1;
        s.end=sys_seconds{start}+hours{12*n};s.start=s.end;
        for(int k=0;k<4;++k){
            UpperLevel lev;
            lev.height_lgl_m=static_cast<float>(500*k);
            lev.height_valid=true;
            lev.temperature_k=static_cast<float>(302-4*k+n);
            lev.temperature_valid=true;
            s.data.push_back(lev);
        }
        upper.soundings.push_back(s);
        layers.push_back({LayerWind{1.f+n,0.f},LayerWind{2.f+n,0.f},
                          LayerWind{3.f+n,0.f}});
        faces.push_back({302.f+n,300.f+n,298.f+n,296.f+n});
    }
    Surface2022 surface;
    surface.station_id=1;
    for(int n=0;n<143;++n) {
        SurfaceInterval s;
        s.start=sys_seconds{start}+hours{n};
        s.end=s.start+hours{1};
        s.obs.temperature_k=285.f+static_cast<float>(n%9);
        s.obs.temperature_valid=true;
        s.obs.humidity_pct=50+n%25;s.obs.humidity_valid=true;
        s.obs.opaque_cloud_tenths=5;s.obs.cloud_valid=true;
        s.obs.precip_code=n==70?0:9999;
        s.obs.precipitation_code_valid=n==70;
        surface.hourly.push_back(s);
    }
    CompBufferedTimeline comp(upper,layers,faces);
    RdsnBufferedTimeline rdsn(surface);
    std::size_t rain_missing=0,rain_observed_zero=0;
    int swapped=0,normal=0;
    for(int n=1;n<=143;++n) {
        auto end=sys_seconds{start}+hours{n};
        auto c=comp.hour(end);
        auto surf=rdsn.select(end-hours{1},end);
        const auto h=p6c_observed_hour(upper,c,surf);
        assert(h.end==end&&h.surface_row==static_cast<std::size_t>(n-1));
        assert(h.gap_seconds==43200);
        assert(h.past_seconds+h.to_go_seconds==h.gap_seconds);
        assert(h.physical_aa_face_t_k.size()==4);
        assert(h.physical_bb_face_t_k.size()==4);
        assert(h.physical_aa.temp_k.size()==4);
        assert(h.surface_temp_k==surface.hourly[n-1].obs.temperature_k);
        if(h.justa<0){
            ++swapped;
            assert(h.aa_slot==1&&h.bb_slot==0);
            assert(h.physical_aa_profile==c.bb_profile);
            assert(h.physical_bb_profile==c.aa_profile);
            assert(h.physical_aa_face_t_k.front()==faces[c.bb_profile].front());
        }else{
            ++normal;
            assert(h.aa_slot==0&&h.bb_slot==1);
            assert(h.physical_aa_profile==c.aa_profile);
            assert(h.physical_bb_profile==c.bb_profile);
            assert(h.physical_aa_face_t_k.front()==faces[c.aa_profile].front());
        }
        if(!h.precipitation_code_observed){
            ++rain_missing;
            assert(h.precipitation_code==9999);
        }else{
            ++rain_observed_zero;
            assert(h.precipitation_code==0);
        }
        if(n==12){
            assert(h.justa==-1&&h.chronological_older==1&&
                   h.chronological_newer==2);
        }
        if(n==13||n==143){
            MixhtObservedMcInput in;
            in.nx=1;in.ny=1;
            apply_p6c_hour_to_mixht_one_station(in,h);
            assert(in.justa.size()==1&&in.justa[0]==h.justa);
            assert(in.sounding[0][0].height_m.size()==4);
            assert(in.nearu.size()==1&&in.nearu[0]==1);
        }
    }
    assert(rain_missing==142&&rain_observed_zero==1);
    assert(swapped>50&&normal>50);
    std::cout<<"PASS_P6E_P6C_143H_HOURLY_BOUNDARY_CONTRACT "
             <<"normal="<<normal<<" swapped="<<swapped
             <<" missing_precip="<<rain_missing
             <<" observed_zero="<<rain_observed_zero<<'\n';
}
