// E21: real-case CALMET option profile semantics through the composed P6E
// chain (MIXHT -> TEMP3D) on a 2-D 50x50 @1 km / NZ=9 field.
//
// Real deck: IMIXH=1 (Maul-Carson), THRESHL=0.0, IZICRLX=1, ISURFT=-1,
// IUPT=-1, ITPROG=0, NOOBS=0, NOWSTA=0, NM3D=0, LCALGRD=T.
// This is a software contract + semantic-consistency gate. Independent
// original-source numerical parity for the same option tuple is produced by
// reference/compare_original_mixht_observed_mc.py.
#include "cteas/p6e/mixht_observed_mc.hpp"
#include "cteas/p6e/realcase_profile.hpp"
#include "cteas/p6e/temp3d_observed_land.hpp"
#include <cassert>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <vector>
using namespace cteas::p6e;
namespace {
constexpr std::size_t NX=50,NY=50,NZ=9,NLEV=10;
template<class F>void fails(F f){bool threw=false;try{f();}catch(const std::invalid_argument&){threw=true;}assert(threw);}
MixdtSounding sounding_profile(float lapse_kperm,float base_k){
    MixdtSounding s;
    const float z[NLEV]={0.f,100.f,250.f,400.f,600.f,850.f,1150.f,1500.f,1900.f,2400.f};
    for(std::size_t k=0;k<NLEV;++k){
        s.height_m.push_back(z[k]);
        s.temp_k.push_back(base_k-lapse_kperm*z[k]);
    }
    return s;
}
MixhtObservedMcInput realcase_grid(int izicrlx){
    MixhtObservedMcInput a;
    a.nx=NX;a.ny=NY;
    a.water_first=50;a.water_last=60;a.iupt=-1;
    a.imixh=1;
    a.izicrlx=izicrlx;a.timestep_s=3600;
    a.constn=2400.f;a.zimin=20.f;a.zimax=2500.f;
    a.threshl=0.f; // real deck THRESHL=0.0
    a.dptmin=0.001f;a.dzzi=200.f;a.onedte=4140.f;a.twodte=1080.f;a.tzicrlx=800.f;
    a.justa={1,-1};
    for(auto& buffer:a.sounding)buffer.resize(2);
    for(std::size_t st=0;st<2;++st)
        for(std::size_t b=0;b<2;++b)
            a.sounding[b][st]=sounding_profile(st==0?0.0075f:0.0085f,300.f);
    const auto n=NX*NY;
    a.nearu.resize(n);a.landuse.resize(n);
    a.qh.resize(n);a.ustar.resize(n);a.el.resize(n);a.rho.resize(n);
    a.cmech.resize(n);a.fcori.resize(n);
    a.initial_zi.assign(n,-7777.f);
    a.initial_ziconv.resize(n);a.initial_dptt.resize(n);
    for(std::size_t i=0;i<NX;++i)for(std::size_t j=0;j<NY;++j){
        const auto k=j*NX+i;
        const bool water=(i+2*j)%23==0;
        const bool night=((i+3*j)%7)==0;
        a.landuse[k]=water?55:12;
        a.nearu[k]=1+static_cast<int>((i+j)%2);
        a.qh[k]=(water||night)?-0.1f:80.f;
        a.el[k]=a.qh[k]<0.f?(20.f+5.f*static_cast<float>((i+j)%4))
                           :-(40.f+20.f*static_cast<float>((i+j)%5));
        a.ustar[k]=0.15f+0.02f*static_cast<float>((i+j)%4);
        a.rho[k]=1.15f;
        a.cmech[k]=110.f;
        a.fcori[k]=0.00007f;
        a.initial_ziconv[k]=water?100.f:(60.f+10.f*static_cast<float>((i+j)%5));
        a.initial_dptt[k]=0.3f;
    }
    return a;
}
}
int main(){
    // 1. The real deck validates and the semantics are reported explicitly.
    RealCaseMicrometProfile real;
    const auto decision=validate_realcase_profile(real);
    assert(decision.scheme==ConvectiveScheme::maul_carson);
    assert(decision.lapse_source==LapseSource::upper_air_soundings);
    assert(decision.two_dimensional_surface_temperature);
    assert(decision.per_cell_lapse_station);
    assert(!decision.land_relaxation_reachable); // THRESHL=0 => IZICRLX inert
    {
        auto p=real;p.threshl_wm2perm=0.02f;
        assert(validate_realcase_profile(p).land_relaxation_reachable);
    }
    {
        auto p=real;p.imixh=-2; // non-critical-path side branch, still reported
        assert(validate_realcase_profile(p).scheme==ConvectiveScheme::batchvarova_gryning);
    }
    // 2. Fail closed outside the source-validated envelope.
    {
        auto p=real;p.irtype=0;fails([&]{return validate_realcase_profile(p);});
        p=real;p.itprog=1;fails([&]{return validate_realcase_profile(p);});
        p=real;p.nm3d=1;fails([&]{return validate_realcase_profile(p);});
        p=real;p.noobs=1;fails([&]{return validate_realcase_profile(p);});
        p=real;p.nowsta=2;fails([&]{return validate_realcase_profile(p);});
        p=real;p.isurft=-2;fails([&]{return validate_realcase_profile(p);});
        p=real;p.isurft=1;fails([&]{return validate_realcase_profile(p);});
        p=real;p.imixh=3;fails([&]{return validate_realcase_profile(p);});
        p=real;p.izicrlx=2;fails([&]{return validate_realcase_profile(p);});
        p=real;p.threshl_wm2perm=-1.f;fails([&]{return validate_realcase_profile(p);});
    }
    // 3. Composed chain on the 2-D real-case field.
    const auto unrelaxed=realcase_grid(0);
    const auto relaxed=realcase_grid(1);
    const auto r0=mixht_observed_mc(unrelaxed);
    const auto r1=mixht_observed_mc(relaxed);
    // THRESHL=0 makes the IZICRLX=1 relaxation branch unreachable, so the
    // real deck's IZICRLX=1 is numerically identical to IZICRLX=0.
    assert(r0.zi==r1.zi&&r0.ziconv==r1.ziconv&&r0.dptt==r1.dptt);
    const auto n=NX*NY;
    assert(r0.zi.size()==n);
    double station1=0.,station2=0.;
    std::size_t count1=0,count2=0,day=0,night=0,water=0;
    for(std::size_t i=0;i<NX;++i)for(std::size_t j=0;j<NY;++j){
        const auto k=j*NX+i;
        if(unrelaxed.landuse[k]==55){
            ++water;
            // Water sentinel: IUPT=-1 and the land-only path leave it alone.
            assert(r0.zi[k]==unrelaxed.initial_zi[k]);
            assert(r0.ziconv[k]==unrelaxed.initial_ziconv[k]);
            continue;
        }
        assert(r0.zi[k]>=unrelaxed.zimin&&r0.zi[k]<=unrelaxed.zimax);
        assert(r0.ziconv[k]>=0.f&&r0.ziconv[k]<=unrelaxed.zimax);
        assert(std::isfinite(r0.dptt[k]));
        if(unrelaxed.qh[k]>=0.f){
            ++day;
            if(unrelaxed.nearu[k]==1){station1+=r0.ziconv[k];++count1;}
            else{station2+=r0.ziconv[k];++count2;}
        }else ++night;
    }
    assert(water>50&&night>50&&day>500&&count1>50&&count2>50);
    // IUPT=-1 resolves the lapse station per cell: the grid cells mapped to
    // the steeper sounding must grow a taller convective layer.
    assert(station2/static_cast<double>(count2)>
           station1/static_cast<double>(count1));
    // 4. ISURFT=-1: the 2-D spatially varying surface temperature reaches
    //    TEMP3D per cell and is preserved exactly on the first model layer.
    Temp3dObservedInput t;
    t.nx=NX;t.ny=NY;t.nz=NZ;
    t.dgrid_m=1000.f;t.irad=1;t.current_hour_utc=6;
    for(std::size_t k=0;k<=NZ;++k)t.face_z_m.push_back(120.f*static_cast<float>(k));
    t.station_x_m={12500.f,37500.f};
    t.station_y_m={12500.f,37500.f};
    t.justa={1,-1};
    t.aa_face_temp_k.assign(2*(NZ+1),0.f);
    t.bb_face_temp_k.assign(2*(NZ+1),0.f);
    for(std::size_t st=0;st<2;++st){
        const float lapse=(st==0)?0.0075f:0.0085f;
        for(std::size_t k=1;k<=NZ;++k){
            const float z=t.face_z_m[k];
            t.aa_face_temp_k[st*(NZ+1)+k]=300.f-lapse*z;
            t.bb_face_temp_k[st*(NZ+1)+k]=299.f-lapse*z;
        }
    }
    t.surface_temp_k.resize(n);
    t.convective_zi_m.resize(n);
    std::size_t distinct=0;
    for(std::size_t k=0;k<n;++k){
        t.surface_temp_k[k]=268.f+2.f*static_cast<float>((k*3+k/7)%7);
        t.convective_zi_m[k]=r0.ziconv[k];
        bool fresh=true;
        for(std::size_t m=0;m<k;++m)
            if(t.surface_temp_k[m]==t.surface_temp_k[k]){fresh=false;break;}
        if(fresh)++distinct;
    }
    assert(distinct>=5); // genuinely 2-D, not a single station value
    const auto column=temp3d_observed_land(t);
    assert(column.size()==n*NZ);
    // TEMP3D output layout is level-major: column[level*n+cell].
    std::size_t perturbed=0;
    for(std::size_t k=0;k<n;++k){
        assert(column[k]==t.surface_temp_k[k]);
        if(k>0&&t.surface_temp_k[k]!=t.surface_temp_k[k-1]){
            assert(column[k]!=column[k-1]);
            ++perturbed;
        }
        for(std::size_t level=0;level<NZ;++level){
            const float v=column[level*n+k];
            assert(std::isfinite(v)&&v>200.f&&v<330.f);
        }
    }
    assert(perturbed>100);
    // 5. Determinism and fail-closed physics inputs.
    assert(temp3d_observed_land(t)==column);
    {
        auto bad=unrelaxed;
        bad.sounding[0][0].height_m[3]=bad.sounding[0][0].height_m[2];
        fails([&]{return mixht_observed_mc(bad);});
    }
    {
        auto bad=unrelaxed;
        for(auto& v:bad.sounding[1][1].temp_k)v=999.9f;
        fails([&]{return mixht_observed_mc(bad);});
    }
    {
        auto bad=t;bad.surface_temp_k.pop_back();
        fails([&]{return temp3d_observed_land(bad);});
    }
    {
        auto bad=t;bad.convective_zi_m[0]=-1.f;
        fails([&]{return temp3d_observed_land(bad);});
    }
}
