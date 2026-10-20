// S4 P6-B2C-1: genuine original-format 1US upper profile forensic input.
// Does not promote PREPDI/INTER2 to native P6 production or modify G20 winds.
// This exports EXACT original RDUPN decoded sounding levels and existing C++
// WIND1 PREPDI upper U/V on the same G19 admissible hour. Independent Fortran
// VERTAV/PREPDI original physics is compiled/rerun separately in CI.
#include "cteas/p6/p6g_g19_file_backed_case.hpp"
#include "cteas/p6/p6g_g20_file_backed_wind1_profiles.hpp"
#include <cmath>
#include <exception>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <string>

int main(int argc,char** argv) {
    try {
        if(argc!=7||std::string(argv[5])!="--out"||
           std::string(argv[6]).empty())
            throw std::invalid_argument(
                "P6-B2C original PREPDI audit requires "
                "<met.inp> <GEO.DAT> <SURF.DAT> <actual original UP.DAT> --out <fresh data>");
        const std::string path=argv[6];
        { std::ifstream previous(path,std::ios::binary);
          if(previous)throw std::invalid_argument(
              "P6-B2C cannot overwrite previous original weather forensic artifact"); }
        cteas::calmet::p6g::G19SourceFilePaths inputs;
        inputs.met_inp=argv[1];
        inputs.geo_dat=argv[2];
        inputs.surf_dat=argv[3];
        inputs.ordered_up_dat.push_back(argv[4]);
        const auto source=cteas::calmet::p6g::g19_load_original_source_case(inputs);
        if(source.stations.surface.size()!=1||
           source.stations.upper.size()!=1||
           cteas::calmet::p6g::g18c1_source_integer(
               source.original_metinp,"NOOBS")!=0||
           cteas::calmet::p6g::g18c1_source_integer(
               source.original_metinp,"IEXTRP")!=-4||
           source.controls.bias.size()!=9)
            throw std::invalid_argument("P6-B2C actual 1SS/1US original IEXTRP=-4 source invalid");
        auto scheduler=source.make_scheduler();
        const auto frame=scheduler.preview_next_hour();
        if(frame.upper.size()!=1||frame.input.upper.size()!=1)
            throw std::invalid_argument("P6-B2C original 1US timing missing");
        const auto& site=frame.upper[0];
        const auto& bracket=frame.input.upper[0];
        if(site.station_id!=source.stations.upper[0].id||
           bracket.earlier>=site.soundings.size()||
           bracket.later>=site.soundings.size()||
           bracket.later!=bracket.earlier+1||
           bracket.span_seconds!=12*3600)
            throw std::invalid_argument("P6-B2C actual 1US observed upper 00/12 source bracket rejected");
        const auto& earlier=site.soundings[bracket.earlier];
        const auto& later=site.soundings[bracket.later];
        if(earlier.end>=frame.input.end||later.end<=frame.input.end||
           earlier.data.size()<2||later.data.size()<2||
           earlier.data.size()>99||later.data.size()>99)
            throw std::invalid_argument("P6-B2C real upper sounding validity/times not accepted");
        const auto profiles=cteas::calmet::p6g::g20_file_backed_source_wind1_profiles(
            frame,true);
        const auto all=source.stations.surface.size()+source.stations.upper.size();
        if(profiles.wind1_u_mps.size()!=9*all||
           profiles.wind1_v_mps.size()!=9*all||
           profiles.wind1_present.size()!=9*all)
            throw std::logic_error("P6-B2C existing PREPDI original wind columns incomplete");
        std::ofstream out(path,std::ios::out|std::ios::trunc);
        if(!out)throw std::runtime_error("P6-B2C forensic new artifact could not be created");
        out<<std::setprecision(std::numeric_limits<float>::max_digits10);
        out<<"P6B2C_ORIGINAL_1US_PREPDI_STAGE_V1\n";
        out<<"SITE "<<site.station_id<<" "<<frame.input.end.time_since_epoch().count()
           <<" "<<earlier.end.time_since_epoch().count()
           <<" "<<later.end.time_since_epoch().count()
           <<" "<<bracket.span_seconds<<" "<<bracket.future_seconds<<" -4\n";
        out<<"ZFACE";
        for(auto z:source.controls.zface_m)out<<" "<<z;
        out<<"\n";
        for(int index=0;index<2;++index) {
            const auto& sounding=index==0?earlier:later;
            out<<"SOUNDING "<<index<<" "<<sounding.data.size()<<"\n";
            for(const auto& layer:sounding.data) {
                if(!std::isfinite(layer.height_lgl_m)||
                   !std::isfinite(layer.u_mps)||
                   !std::isfinite(layer.v_mps))
                    throw std::invalid_argument("P6-B2C original decoded IGRA UP nonfinite");
                out<<layer.height_lgl_m<<" "<<layer.u_mps<<" "<<layer.v_mps<<"\n";
            }
        }
        out<<"NATIVE 9\n";
        for(std::size_t k=0;k<9;++k) {
            const auto idx=k*all+1;
            if(profiles.wind1_present[idx]!=1U||
               !std::isfinite(profiles.wind1_u_mps[idx])||
               !std::isfinite(profiles.wind1_v_mps[idx]))
                throw std::invalid_argument("P6-B2C real original upper WIND1 wind not valid");
            out<<(k+1)<<" "<<profiles.wind1_u_mps[idx]
               <<" "<<profiles.wind1_v_mps[idx]<<"\n";
        }
        out.flush();
        if(!out)throw std::runtime_error("P6-B2C original weather evidence output incomplete");
        if(scheduler.completed_hours()!=0)
            throw std::logic_error("P6-B2C source only accidentally committed a model hour");
        std::cout<<"P6_B2C_TRUE_SOURCE_1US_PREPDI_RAW_AND_NATIVE_EXPORTED_FOR_VENDOR_CHECK"
                 <<" ORIGINAL_STATION_ID="<<site.station_id
                 <<" OBSERVED_BRACKET_SECONDS="<<bracket.span_seconds
                 <<" IEXTRP=-4 FIRST_LAYER_INTER2=UNVERIFIED"
                 <<" G23=NOT_RUN P6_SCIENCE=NOT_ACCEPTED\n";
        return 0;
    } catch(const std::exception& e) {
        std::cerr<<"P6_B2C_REAL_1US_PREPDI_SOURCE_REJECTED "<<e.what()<<"\n";
        return 2;
    }
}
