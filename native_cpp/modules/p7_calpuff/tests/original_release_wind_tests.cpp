#include "cteas/puff/original_release_wind.hpp"
#include <array>
#include <bit>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
using namespace cteas::puff;
namespace {
void require(bool p,const char* reason){
    if(!p)throw std::runtime_error(reason);
}
template<class Fn> void refuses(Fn&& fn) {
    bool threw=false;try{fn();}catch(const std::exception&){threw=true;}
    require(threw,"unsupported RLSMET/WINDSET input was accepted");
}
void synthetic() {
    OriginalMetHour m;
    m.nx=3;m.ny=3;m.nz=3;
    m.u.assign(27,1.0F);
    m.v.assign(27,0.0F);
    // Release is at level 2 with 3-4-5 triangle.
    for(std::size_t i=9;i<18;++i) {m.u[i]=3.0F;m.v[i]=4.0F;}
    Calmet21Static s;
    s.cell_face_m={0,100,200,300};
    s.roughness_m.assign(9,0.25F);
    const OriginalReleaseWindRequest req{.x_cells=1.5F,
        .y_cells=1.5F,.release_height_m=150.0F,.calm_threshold_ms=0.5F};
    const auto native=original_release_wind_metfm1(m,s,req);
    require(native.cell.ix_1based==2 && native.cell.iy_1based==2 &&
            native.layer_1based==2 && native.wind_speed_raw_ms==5.0F &&
            native.wind_speed_ms==5.0F && !native.calm,
            "native original WINDSET did not use RLSMET ZFIND layer");
    ReleaseCadenceInputs schedule;
    schedule.emission_interval=36.0;
    schedule.max_puffs=99;
    schedule.hour_seconds=3600;
    schedule.wind_speed_ms=1111; // must be overwritten by genuine wind
    const auto puff=original_points1_cadence_from_release_wind(
        m,s,req,50.0F,schedule);
    require(puff.puff_count==99 &&
            puff.emission_duration_s==static_cast<float>(3600.0F/99.0F),
            "native RLSMET WINDSET did not feed POINTS1 WSNEW");
    // wind 1 m/s at level 1 → INT(36)+1=37.
    auto low=req;low.release_height_m=50.0F;
    const auto n=original_points1_cadence_from_release_wind(m,s,low,50.0F,schedule);
    require(n.puff_count==37,"level-dependent native NPUFFS not applied");
    // The original explicitly selects AMAX1(stack WS, final-rise WS).
    // Even if a final height has a lower wind, a faster stack-layer
    // wind determines the release count.
    const auto stack_dominant=original_points1_cadence_from_release_wind(
        m,s,low,150.0F,schedule);
    require(stack_dominant.puff_count==99,
            "POINTS1 omitted stack WS in max(stack,final)");
    // A calm zero-wind must retain the original WDCALM and minimum
    // transport speed of 0.001, without forcing a 0.5 m/s substitute.
    m.u.assign(27,0);m.v.assign(27,0);
    const auto calm=original_release_wind_metfm1(m,s,req);
    require(calm.calm && calm.wind_speed_raw_ms==0.0F &&
            calm.wind_speed_ms==0.001F && calm.wind_direction_deg==180.0F &&
            calm.flow_deg==0.0F && calm.vector_direction_deg==0,
            "original RLSMET calm branch diverged");
    auto nonfinite=req;nonfinite.release_height_m=std::nanf("");
    refuses([&]{(void)original_release_wind_metfm1(m,s,nonfinite);});
    s.roughness_m.clear();
    refuses([&]{(void)original_release_wind_metfm1(m,s,req);});
}
struct DgmFirst {std::array<std::int32_t,24> ints;std::array<float,64> floats;};
static_assert(sizeof(DgmFirst)==352);
static_assert(std::endian::native==std::endian::little);
void real_first_hour(const std::string& met_path,const std::string& dgm_path){
    std::ifstream dump(dgm_path,std::ios::binary);
    require(static_cast<bool>(dump),"original 2022 first-hour DGM absent");
    DgmFirst first{};
    require(static_cast<bool>(dump.read(reinterpret_cast<char*>(&first),sizeof(first))),
            "original first DGM record unreadable");
    require(first.ints[0]==1 && first.ints[1]==202200100 &&
            first.ints[12]==0,"wrong original first-hour DGM record");
    std::size_t checked=0;
    OriginalMetHourlyReader::read(met_path,
      [&](const Calmet21Header& header,const Calmet21Static& static_met,
          const OriginalMetHour& hour) {
        if(checked!=0)return;
        require(header.nx==50 && header.ny==50 && header.nz==9,
                "frozen original MET dimensions changed");
        const auto observed=original_release_wind_metfm1(hour,static_met,{
            .x_cells=first.floats[0],.y_cells=first.floats[1],
            .release_height_m=first.floats[2],
            .calm_threshold_ms=0.5F
        });
        const float orig=first.floats[18]; // DGM WSVAR from original COMP
        const auto stack_wind=original_release_wind_metfm1(hour,static_met,{
            .x_cells=first.floats[0],.y_cells=first.floats[1],
            .release_height_m=70.8F,.calm_threshold_ms=0.5F
        });
        const float wsnew=std::max(stack_wind.wind_speed_ms,
                                   observed.wind_speed_ms);
        const auto rel=std::abs(wsnew-orig);
        std::cout<<"P7_NATIVE_RELEASE_WIND_FIRST_HOUR"
                 <<" ORIGINAL_WSVAR="<<orig
                 <<" NATIVE_WSNEW="<<wsnew
                 <<" STACK_WS="<<stack_wind.wind_speed_ms
                 <<" FINAL_WS="<<observed.wind_speed_ms
                 <<" LAYER="<<observed.layer_1based
                 <<" DIFFERENCE="<<rel<<"\n";
        require(rel<0.00002F,
                "first-hour original WSVAR differs: original POINTS1 WSNEW or HEFF/GRID mismatch");
        ReleaseCadenceInputs schedule;
        schedule.wind_speed_ms=-100.0;
        schedule.emission_interval=36.0;
        schedule.hour_seconds=3600.0;
        schedule.max_puffs=99;
        const auto release=original_points1_cadence_from_release_wind(
            hour,static_met,{
              .x_cells=first.floats[0],.y_cells=first.floats[1],
              .release_height_m=first.floats[2],.calm_threshold_ms=0.5F
            },70.8F,schedule);
        require(release.puff_count==54,
                "native original source wind cannot reproduce first-hour 54 POINTS1 puffs");
        ++checked;
      },true);
    require(checked==1,"frozen first-hour MET record absent");
    std::cout<<"P7_NATIVE_WINDSET_RLSMET_RELEASE=PASS"
             <<" FROZEN_FIRST_HOUR_POINT_COUNT=54"
             <<" ORIGINAL_143H_FULL_RLSMET=NOT_YET_ACCEPTED\n";
}
void full_original_release_wind_143h(
    const std::string& met_path,const std::string& dgm_path){
    // DGM is a read-only independent vendor Fortran oracle. Extract its
    // initial height and first new-puff WSVAR per hour, then derive WSNEW
    // independently from hourly CALMET with selected native WINDSET.
    // Original release heights remain oracle-fed here (PRFIN is NOT closed).
    std::ifstream binary(dgm_path,std::ios::binary);
    require(static_cast<bool>(binary),"original 143h DGM unavailable");
    DgmFirst rec{};
    bool available=static_cast<bool>(
        binary.read(reinterpret_cast<char*>(&rec),sizeof(rec)));
    require(available,"empty original 143h DGM");
    std::size_t completed=0,wind_errors=0,count_errors=0,total_puffs=0;
    double max_wind_error=0.0;
    const auto summary=OriginalMetHourlyReader::read(met_path,
      [&](const Calmet21Header& header,const Calmet21Static& statics,
          const OriginalMetHour& hour){
        if(completed>=143)return;
        const int packed=hour.begin.year*100000+
                         hour.begin.julian_day*100+hour.begin.hour;
        require(header.nx==50 && header.ny==50 && header.nz==9,
                "original 2022 143h wind met dimensions drifted");
        require(hour.begin.year==2022 &&
                static_cast<int>(completed)==
                   (hour.begin.julian_day-1)*24+hour.begin.hour,
                "143h original MET time ordering changed");
        require(available && rec.ints[1]==packed,
                "missing original DGM puff records at MET hour");
        bool found_new=false;
        DgmFirst first_new{};
        while(available && rec.ints[1]==packed){
            if(!found_new && rec.ints[12]==0){
                first_new=rec;
                found_new=true;
            }
            available=static_cast<bool>(
                binary.read(reinterpret_cast<char*>(&rec),sizeof(rec)));
        }
        require(found_new,"no original POINTS1 new puff in DGM hour");
        const float orig=first_new.floats[18];
        const OriginalReleaseWindRequest location{
            .x_cells=first_new.floats[0],
            .y_cells=first_new.floats[1],
            .release_height_m=first_new.floats[2],
            .calm_threshold_ms=0.5F
        };
        const auto native=original_release_wind_metfm1(
            hour,statics,location);
        const auto stack=original_release_wind_metfm1(hour,statics,{
            .x_cells=location.x_cells,.y_cells=location.y_cells,
            .release_height_m=70.8F,.calm_threshold_ms=0.5F
        });
        const float wsnew=std::max(stack.wind_speed_ms,native.wind_speed_ms);
        const double delta=std::abs(static_cast<double>(orig)-
                                    static_cast<double>(wsnew));
        max_wind_error=std::max(max_wind_error,delta);
        if(delta>2e-5){
            if(wind_errors==0)
                std::cerr<<"P7_143H_NATIVE_RLSMET_FIRST_WIND_DIFFERENCE"
                         <<" HOUR="<<completed
                         <<" PACKED="<<packed
                         <<" X="<<location.x_cells
                         <<" Y="<<location.y_cells
                         <<" ORIGINAL_HEIGHT="<<location.release_height_m
                         <<" ORIGINAL_WS="<<orig
                         <<" NATIVE_WS="<<wsnew
                         <<" STACK_WS="<<stack.wind_speed_ms
                         <<" FINAL_WS="<<native.wind_speed_ms
                         <<" DELTA="<<delta<<"\n";
            ++wind_errors;
        }
        ReleaseCadenceInputs q;
        q.max_puffs=99;
        q.hour_seconds=3600.0;
        q.emission_interval=3600.0/header.dx_m;
        const auto predicted=original_points1_cadence_from_release_wind(
            hour,statics,location,70.8F,q);
        const int originally_scheduled=first_new.ints[10]; // new NSAM
        if(predicted.puff_count!=originally_scheduled){
            if(count_errors==0)
                std::cerr<<"P7_143H_POINT_RELEASE_FIRST_COUNT_DIFFERENCE"
                         <<" HOUR="<<completed
                         <<" PACKED="<<packed
                         <<" NATIVE_NPUFFS="<<predicted.puff_count
                         <<" ORIGINAL_NEW_NSAM="<<originally_scheduled
                         <<" ORIGINAL_WS="<<orig<<"\n";
            ++count_errors;
        }
        total_puffs+=static_cast<std::size_t>(predicted.puff_count);
        ++completed;
    },true);
    require(summary.intervals==143 && completed==143,
            "native 143h RLSMET selected release-hour count incomplete");
    std::cout<<"P7_143H_NATIVE_WINDSET_RLSMET_ORIGINAL_HEIGHT_FED"
             <<" HOURS="<<completed
             <<" WSVAR_MISMATCH="<<wind_errors
             <<" NEW_NSAM_MISMATCH="<<count_errors
             <<" NATIVE_RELEASE_PUFFS="<<total_puffs
             <<" MAX_WS_ERROR="<<max_wind_error
             <<" ORIGINAL_PRFIN_HEIGHT_FED=YES"
             <<" SOURCE_STACK_HEIGHT=70.8"
             <<" WSNEW_RULE=MAX_STACK_FINAL"
             <<" AUTONOMOUS_FROZEN_COMP=NOT_YET_VALIDATED\n";
    require(wind_errors==0,"143h original release WSVAR mismatch");
    require(count_errors==0,"143h original new-puff cadence mismatch");
    require(total_puffs==11985U,
            "143h independent release count not equal original 11985");
}
}
int main(int argc,char** argv){
    try{
        synthetic();
        if(argc==3) real_first_hour(argv[1],argv[2]);
        else if(argc==4 && std::string(argv[3])=="143")
            full_original_release_wind_143h(argv[1],argv[2]);
        else if(argc!=1)throw std::invalid_argument("expected [met.dat dgm.bin [143]]");
        std::cout<<"P7_NATIVE_WINDSET_METFM1=PASS SOURCE_SELECTED=YES\n";
        return 0;
    }catch(const std::exception& e){
        std::cerr<<"P7_NATIVE_WINDSET_METFM1=FAIL "<<e.what()<<"\n";
        return 1;
    }
}
