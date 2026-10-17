// P6C actual GEO/SURF/UP 2022 joint input state, selected one-station case.
// Output is a trace for independent source-backed checks, NOT CALMET.DAT.
#include "cteas/p6/comp_buffered_timeline.hpp"
#include "cteas/p6/read_geo.hpp"
#include "cteas/p6/surface_hourly_state.hpp"
#include <chrono>
#include <exception>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
int main(int argc,char** argv) {
    if(argc!=10) {
        std::cerr<<"usage: cteas_p6_comp_joint GEO.DAT SURF.DAT UP.DAT OUT.csv UPPER_STATION XORIGKM YORIGKM\n";
        return 2;
    }
    try {
        using namespace cteas::calmet::p6;
        const auto geo=read_geo_50(argv[1],std::stod(argv[6]),std::stod(argv[7]));
        const auto surf=read_surface_2022(argv[2]);
        const auto upper=read_upper_2022(argv[3],std::stoi(argv[5]));
        const std::vector<float> faces{0,20,40,80,160,320,640,1200,2000,3000};
        const auto hours=comp_selected_2022_hours(upper,faces,std::stoi(argv[8]),std::stoi(argv[9]));
        if(surf.hourly.size()!=hours.size()||hours.size()!=143)
            throw std::runtime_error("COMP-SURF interval count mismatch");
        RdsnBufferedTimeline surface_state(surf,std::stoi(argv[8]));
        std::ofstream out(argv[4]);
        if(!out)throw std::runtime_error("COMP output CSV inaccessible");
        out<<"hour_index,start_epoch_s,end_epoch_s,geo_center_terrain_m,geo_center_z0_m,"
              "surf_station_id,upper_station_id,surf_ws,surf_wd,surf_cloud,surf_temp_k,"
              "surf_precip_code,wind_valid,cloud_valid,temp_valid,precip_valid,"
              "surf_ceiling,surf_rh,surf_pres,surf_ceiling_valid,surf_rh_valid,surf_pres_valid,"
              "rdsn_record_index,rdsn_reads,rdsn_reused,"
              "aa_index,bb_index,aa_slot,bb_slot,jorder,turnovers,total_reads,"
              "elapsed_s,to_go_s,gap_s,layer,upper_u,upper_v,"
              "aa_temp_face_low_k,aa_temp_face_high_k,bb_temp_face_low_k,bb_temp_face_high_k\n";
        out<<std::fixed<<std::setprecision(9);
        int no_rain=0;
        for(std::size_t n=0;n<hours.size();++n) {
            const auto& h=hours[n];
            const auto surface=surface_state.select(
                h.interpolated.end-std::chrono::hours{1},h.interpolated.end);
            const auto& sf=*surface.record;
            if(sf.end!=h.interpolated.end ||
               sf.start!=h.interpolated.end-std::chrono::hours{1})
                throw std::runtime_error("COMP-SURF clock/endtime mismatch");
            if(h.interpolated.winds.size()!=9 ||
               h.aa_face_temperature_k.size()!=10 ||
               h.bb_face_temperature_k.size()!=10)
                throw std::runtime_error("COMP 9-layer/10-face physical grids invalid");
            if(!sf.obs.precipitation_code_valid)++no_rain;
            for(std::size_t k=0;k<9;++k) {
                const auto& v=sf.obs;
                const auto& w=h.interpolated.winds[k];
                constexpr std::size_t center=24*50+24;
                out<<n+1<<','<<sf.start.time_since_epoch().count()<<','
                   <<sf.end.time_since_epoch().count()<<','
                   <<geo.terrain_m[center]<<','<<geo.z0_m[center]<<','
                   <<surf.station_id<<','<<upper.station_id<<','
                   <<v.wind_speed_mps<<','<<v.wind_direction_deg<<','
                   <<v.opaque_cloud_tenths<<','<<v.temperature_k<<','
                   <<v.precip_code<<','<<v.wind_valid<<','<<v.cloud_valid
                   <<','<<v.temperature_valid<<','<<v.precipitation_code_valid<<','
                   <<v.ceiling_hundreds_ft<<','<<v.humidity_pct<<','<<v.pressure_mb<<','
                   <<v.ceiling_valid<<','<<v.humidity_valid<<','<<v.pressure_valid<<','
                   <<surface.source_row+1<<','<<surface.reads<<','<<surface.reused<<','
                   <<h.aa_profile+1<<','<<h.bb_profile+1<<','
                   <<h.aa_slot<<','<<h.bb_slot<<','<<h.jorder<<','
                   <<h.turnovers<<','<<h.total_reads<<','
                   <<h.interpolated.past_seconds<<','
                   <<h.interpolated.to_go_seconds<<','
                   <<h.interpolated.gap_seconds<<','<<k+1<<','
                   <<w.u_mps<<','<<w.v_mps<<','
                   <<h.aa_face_temperature_k[k]<<','
                   <<h.aa_face_temperature_k[k+1]<<','
                   <<h.bb_face_temperature_k[k]<<','
                   <<h.bb_face_temperature_k[k+1]<<'\n';
            }
        }
        if(!out)throw std::runtime_error("COMP output CSV incomplete");
        std::cout<<"P6C_SELECTED_JOINT_TRACE hours="<<hours.size()
                 <<" rows="<<hours.size()*9
                 <<" missing_precip_hours="<<no_rain
                 <<" SOURCE_EXACT_COMP_NOT_YET_PROVEN\n";
        return 0;
    }catch(const std::exception& e) {
        std::cerr<<"P6C_COMP_JOINT_ERROR: "<<e.what()<<'\n';
        return 1;
    }
}
