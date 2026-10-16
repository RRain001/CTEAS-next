// Synthetic AVETMP checks with explicitly constructed u/v inputs.
// These are unit-level software checks; the original-source comparison is
// reference/compare_original_avetmp.py.
#include "cteas/p6e/avetmp.hpp"
#include <cassert>
#include <cmath>
#include <stdexcept>
#include <vector>
using namespace cteas::p6e;
namespace {
template<class F>void fails(F f){bool threw=false;try{f();}catch(const std::invalid_argument&){threw=true;}assert(threw);}
AvetmpInput grid(int nx,int ny,int mnmdav,float hafang,float dgrid){
    AvetmpInput a;
    a.nx=static_cast<std::size_t>(nx);a.ny=static_cast<std::size_t>(ny);
    a.mnmdav=mnmdav;a.hafang_deg=hafang;a.dgrid_m=dgrid;
    const auto n=a.nx*a.ny;
    a.u_ms.assign(n,0.f);a.v_ms.assign(n,0.f);a.temperature_k.assign(n,280.f);
    return a;
}
}
int main(){
    // 1. A constant field survives any wind exactly.
    {
        auto a=grid(6,5,2,30.f,100.f);
        for(std::size_t k=0;k<a.u_ms.size();++k){
            a.u_ms[k]=2.f+0.1f*static_cast<float>(k%3);
            a.v_ms[k]=-1.f-0.05f*static_cast<float>(k%4);
        }
        const auto out=avetmp(a);
        for(const float v:out)assert(std::fabs(v-280.f)<1e-4f);
    }
    // 2. A 1x1 grid only ever averages the local cell.
    {
        auto a=grid(1,1,1,45.f,100.f);
        a.temperature_k[0]=301.25f;a.u_ms[0]=3.f;a.v_ms[0]=4.f;
        const auto out=avetmp(a);
        assert(out.size()==1U&&out[0]==301.25f);
    }
    // 3. Zero wind falls back to the distance weight and spreads a hot cell.
    {
        auto a=grid(7,7,3,30.f,100.f);
        const auto centre=static_cast<std::size_t>(3)*7U+3U;
        a.temperature_k[centre]=300.f;
        const auto out=avetmp(a);
        assert(out[centre]<300.f);
        assert(out[0]>280.f&&out[0]<300.f);
        for(const float v:out)assert(std::isfinite(v)&&v>=279.9f&&v<=300.1f);
    }
    // 4. Downwind advection: the plume shifts with the wind direction.
    {
        auto a=grid(9,9,2,30.f,100.f);
        const auto centre=static_cast<std::size_t>(4)*9U+4U;
        a.temperature_k[centre]=300.f;
        for(std::size_t k=0;k<a.u_ms.size();++k){a.u_ms[k]=3.f;a.v_ms[k]=0.f;}
        const auto east=avetmp(a);
        auto b=a;
        for(std::size_t k=0;k<b.u_ms.size();++k){b.u_ms[k]=-3.f;}
        const auto west=avetmp(b);
        const auto east_cell=static_cast<std::size_t>(4)*9U+5U;
        const auto west_cell=static_cast<std::size_t>(4)*9U+3U;
        // The weight favours cells upwind of each point, so the hot cell is
        // advected downstream: with u>0 the eastern neighbour is warmed.
        assert(east[east_cell]>east[west_cell]);
        assert(west[west_cell]>west[east_cell]);
    }
    // 5. Determinism and fail-closed validation.
    {
        auto a=grid(5,4,1,30.f,100.f);
        const auto first=avetmp(a);
        assert(avetmp(a)==first);
        auto bad=a;bad.u_ms.pop_back();fails([&]{return avetmp(bad);});
        auto bad2=a;bad2.temperature_k[0]=std::nanf("");fails([&]{return avetmp(bad2);});
        auto bad3=a;bad3.dgrid_m=0.f;fails([&]{return avetmp(bad3);});
        auto bad4=a;bad4.mnmdav=-1;fails([&]{return avetmp(bad4);});
    }
}
