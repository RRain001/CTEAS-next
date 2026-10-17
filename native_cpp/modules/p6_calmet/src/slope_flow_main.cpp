#include "cteas/p6/slope_flow.hpp"
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
using cteas::calmet::p6::SlopeInput;
using cteas::calmet::p6::compute_original_slope_scoped;
namespace {
template<class T> void read_values(std::istream& in, std::vector<T>& xs) {
    for (auto& x:xs) if (!(in>>x)) throw std::runtime_error("SLOPE truncated input");
}
}
int main(int argc,char** argv) {
    try {
        if (argc!=3) throw std::invalid_argument("usage: cteas_p6_slope INPUT OUTPUT.csv");
        std::ifstream in(argv[1]);
        if (!in) throw std::runtime_error("SLOPE failed opening input");
        SlopeInput x;
        if (!(in>>x.nx>>x.ny>>x.nz>>x.dx_m>>x.dy_m>>
                 x.water_first>>x.water_last>>x.isurft>>x.domain_temperature_k))
            throw std::runtime_error("SLOPE invalid input header");
        if (x.nx<2 || x.ny<2 || x.nz<1 || x.nx>400 || x.ny>400 || x.nz>12)
            throw std::runtime_error("SLOPE dimensions out of range");
        const auto n=std::size_t(x.nx)*std::size_t(x.ny);
        x.zface_m.resize(std::size_t(x.nz+1));
        for (auto* v:{&x.terrain_m,&x.hmax_m,&x.hmin_m,
                      &x.disthmax_m,&x.disthmin_m,
                      &x.sensible_heat_w_m2,&x.surface_temperature_k}) v->resize(n);
        x.landuse.resize(n);
        read_values(in,x.zface_m);
        read_values(in,x.terrain_m);
        read_values(in,x.hmax_m);
        read_values(in,x.hmin_m);
        read_values(in,x.disthmax_m);
        read_values(in,x.disthmin_m);
        read_values(in,x.sensible_heat_w_m2);
        read_values(in,x.surface_temperature_k);
        read_values(in,x.landuse);
        std::string surplus;
        if (in>>surplus) throw std::runtime_error("SLOPE unexpected trailing input");
        const auto wind=compute_original_slope_scoped(x);
        std::ofstream out(argv[2]);
        if (!out) throw std::runtime_error("SLOPE failed opening output");
        out<<"i,j,k,u_mps,v_mps\n"<<std::setprecision(11);
        for (int k=0;k<x.nz;++k) for(int j=0;j<x.ny;++j) for(int i=0;i<x.nx;++i) {
            auto index=std::size_t(k)*n+std::size_t(j)*std::size_t(x.nx)+std::size_t(i);
            out<<i+1<<','<<j+1<<','<<k+1<<','<<wind.u_mps[index]<<','<<wind.v_mps[index]<<'\n';
        }
        if (!out) throw std::runtime_error("SLOPE output write failed");
        return 0;
    } catch(const std::exception& ex) {
        std::cerr<<ex.what()<<'\n';
        return 1;
    }
}
