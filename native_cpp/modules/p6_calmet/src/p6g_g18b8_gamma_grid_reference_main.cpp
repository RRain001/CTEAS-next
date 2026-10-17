// G18B8 source GAMMA C++ numerical oracle for literal vendor CALMET DIAGNO.
// stdin: NX NY NUSTA IUPT DGRID_M; then NUSTA X Y GAMUP rows.
// stdout: GAMMA(I,J) grid REAL*4 scientific, J-major/I-minor.
#include "cteas/p6/p6g_g18b8_gamma_grid.hpp"
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <vector>
int main() {
    try {
        int nx=0,ny=0,nu=0,iupt=0;
        float spacing=0.f;
        if(!(std::cin>>nx>>ny>>nu>>iupt>>spacing)||
           nx<2||ny<2||nx>100||ny>100||nu<1||nu>6||
           (iupt!=-1&&(iupt<1||iupt>nu))||
           !std::isfinite(spacing)||spacing<=0.f)
            throw std::invalid_argument("G18B8 source field header invalid");
        cteas::calmet::p6g::GeoGrid grid;
        grid.nx=nx;grid.ny=ny;grid.grid_km=spacing/1000.f;
        cteas::calmet::p6g::StationSet stations;
        cteas::calmet::p6g::G18B4CGammaPrepared prepared;
        for(int i=0;i<nu;++i) {
            cteas::calmet::p6::DeckStation us{};
            us.id=58424+i;
            float value=0.f;
            if(!(std::cin>>us.local_x_m>>us.local_y_m>>value))
                throw std::invalid_argument("G18B8 original upper coordinates/lapse missing");
            stations.upper.push_back(us);
            prepared.station_ids.push_back(us.id);
            cteas::calmet::p6::CGammaResult gamma;
            gamma.kelvin_per_m=value;
            prepared.lapse.push_back(gamma);
        }
        cteas::calmet::p6g::G18B3UpperChoice choice;
        choice.iupt=iupt;
        choice.nearu.assign(static_cast<std::size_t>(nx)*ny,1);
        const auto result=cteas::calmet::p6g::g18b8_source_gamma_grid(
            grid,stations,choice,prepared,true);
        std::cout<<std::scientific<<std::setprecision(10);
        for(const float v:result.gamma_k_per_m)
            std::cout<<v<<"\n";
        return 0;
    }catch(const std::exception& e) {
        std::cerr<<"G18B8_SOURCE_GAMMA_FAIL "<<e.what()<<"\n";
        return 1;
    }
}
