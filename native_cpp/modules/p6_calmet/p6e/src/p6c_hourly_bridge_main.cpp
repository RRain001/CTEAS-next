// P6E 2022 input-ingestion boundary. Executes real P6C selected
// SURF.DAT/RDSN + UP.DAT/COMP readers, records their typed hourly
// surface and AA/BB physical profiles for P6E, without using P6D
// or pretending that it has computed MET.DAT/any 3D meteorology.
#include "cteas/p6e/p6c_hourly_bridge.hpp"
#include <chrono>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <ostream>
#include <stdexcept>
#include <string>
#include <vector>

int main(int argc,char** argv) {
    if(argc!=5) {
        std::cerr<<"usage: p6e_p6c_hourly_bridge SURF.DAT UP.DAT UPPER_STATION OUT.csv\n";
        return 2;
    }
    try {
        using namespace cteas::calmet::p6;
        using namespace cteas::p6e;
        using namespace std::chrono;
        const auto surface=read_surface_2022(argv[1]);
        const auto upper=read_upper_2022(argv[2],std::stoi(argv[3]));
        // Freeze the same P6C selected 9-layer/10-face geometry as
        // the original CTEAS 2022 case's COMP joint reader.
        const std::vector<float> faces{0.f,20.f,40.f,80.f,160.f,
                                       320.f,640.f,1200.f,2000.f,3000.f};
        const auto hourly_states=comp_selected_2022_hours(upper,faces);
        if(hourly_states.size()!=143||surface.hourly.size()!=143)
            throw std::runtime_error("P6E source input not exactly 143 hours");
        RdsnBufferedTimeline rdsn(surface);
        std::ofstream out(argv[4]);
        if(!out)throw std::runtime_error("P6E hourly trace cannot be opened");
        out<<"hour_index,end_epoch_s,rdsn_source_row,upper_station_id,"
              "chronological_old_index,chronological_new_index,"
              "physical_aa_index,physical_bb_index,justa,aa_slot,bb_slot,"
              "past_s,to_go_s,gap_s,air_temperature_k,pressure_mb,humidity_pct,"
              "opaque_cloud_tenths,ceiling_hundreds_ft,precipitation_code,precipitation_observed,"
              "physical_aa_face2_k,physical_bb_face2_k,"
              "physical_aa_sounding_level1_k,physical_bb_sounding_level1_k,"
              "aa_profile,bb_profile,aa_face_t,bb_face_t\n";
        out<<std::fixed<<std::setprecision(7);
        int missing_precip=0,observed_zero=0,negative_order=0;
        for(std::size_t n=0;n<hourly_states.size();++n) {
            const auto& h=hourly_states[n];
            const auto surface_state=rdsn.select(
                h.interpolated.end-hours{1},h.interpolated.end);
            const auto row=p6c_observed_hour(upper,h,surface_state);
            if(row.physical_aa_face_t_k.size()!=10||
               row.physical_bb_face_t_k.size()!=10||
               h.interpolated.winds.size()!=9)
                throw std::runtime_error("P6E real 2022 model face/layer count drift");
            if(!row.precipitation_code_observed)++missing_precip;
            if(row.precipitation_code_observed && row.precipitation_code==0)
                ++observed_zero;
            if(row.justa<0)++negative_order;
            const auto end_epoch=duration_cast<seconds>(
                row.end.time_since_epoch()).count();
            out<<n+1<<','<<end_epoch<<','<<row.surface_row+1<<','
               <<upper.station_id<<','
               <<row.chronological_older+1<<','
               <<row.chronological_newer+1<<','
               <<row.physical_aa_profile+1<<','
               <<row.physical_bb_profile+1<<','
               <<row.justa<<','<<row.aa_slot<<','<<row.bb_slot<<','
               <<row.past_seconds<<','<<row.to_go_seconds<<','
               <<row.gap_seconds<<','<<row.surface_temp_k<<','
               <<row.surface_pressure_mb<<','
               <<row.surface_humidity_pct<<','
               <<row.opaque_cloud_tenths<<','
               <<row.ceiling_hundreds_ft<<','
               <<row.precipitation_code<<','
               <<static_cast<int>(row.precipitation_code_observed)<<','
               <<row.physical_aa_face_t_k[1]<<','
               <<row.physical_bb_face_t_k[1]<<','
               <<row.physical_aa.temp_k[0]<<','
               <<row.physical_bb.temp_k[0];
            // Profiles are packed as "height:temperature;..." so the column
            // set does not depend on the sounding level count.
            const auto pack_profile=[](std::ostream& stream,
                                       const std::vector<float>& height,
                                       const std::vector<float>& temp) {
                if(height.size()!=temp.size())
                    throw std::runtime_error("P6C bridge profile size mismatch");
                for(std::size_t k=0;k<height.size();++k)
                    stream<<(k?';':',')<<height[k]<<':'<<temp[k];
            };
            pack_profile(out,row.physical_aa.height_m,row.physical_aa.temp_k);
            pack_profile(out,row.physical_bb.height_m,row.physical_bb.temp_k);
            const auto pack_faces=[](std::ostream& stream,
                                     const std::vector<float>& values) {
                for(std::size_t k=0;k<values.size();++k)
                    stream<<(k?';':',')<<values[k];
            };
            pack_faces(out,row.physical_aa_face_t_k);
            pack_faces(out,row.physical_bb_face_t_k);
            out<<'\n';
        }
        if(!out)throw std::runtime_error("P6E hourly CSV write incomplete");
        std::cout<<"P6E_P6C_2022_HOURLY_BRIDGE_SOURCE_INPUT "
                 <<"hours=143 missing_precip_hours="<<missing_precip
                 <<" observed_zero_precip_hours="<<observed_zero
                 <<" reversed_AABB_hours="<<negative_order
                 <<" IS_COMP_INPUT_CONTRACT_ONLY=1"
                 <<" PHYSICS_AND_2022_ORIGINAL_MET_PARITY_NOT_PROVEN=1\n";
        return 0;
    } catch(const std::exception& ex) {
        std::cerr<<"P6E_P6C_2022_BRIDGE_ERROR: "<<ex.what()<<'\n';
        return 1;
    }
}
