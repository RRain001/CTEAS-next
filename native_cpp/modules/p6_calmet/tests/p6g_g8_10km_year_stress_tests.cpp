#include "cteas/p6/p6g_case_loader.hpp"
#include "cteas/p6/p6g_g17b_observed_solar_heat.hpp"
#include "cteas/p6/p6g_selected_hour_bridge.hpp"
#include "cteas/p6/p6g_observed_thermal_hour.hpp"
#include "cteas/p6/read_geo_dynamic.hpp"
#include <bit>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <exception>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

using namespace std::chrono;
using namespace cteas::calmet::p6g;

static void require_test(bool ok,const char* message) {
    if(!ok)throw std::runtime_error(message);
}
static int day_of_year(sys_seconds instant) {
    const auto d=floor<days>(instant);
    return static_cast<int>((d-sys_days{year_month_day{d}.year()/January/1}).count())+1;
}
static void stamp(std::ostream& out,sys_seconds when,bool hour24=false) {
    if(hour24&&when==floor<days>(when)){
        when-=hours{1};
        const auto ymd=year_month_day{floor<days>(when)};
        out<<int(ymd.year())<<" "<<day_of_year(when)<<" 24 0";
        return;
    }
    const auto ymd=year_month_day{floor<days>(when)};
    out<<int(ymd.year())<<" "<<day_of_year(when)<<" "
       <<duration_cast<hours>(when-floor<days>(when)).count()<<" 0";
}
static void write_surface(const std::string& path,sys_seconds begin,
                          sys_seconds end) {
    std::ofstream out(path);
    require_test(static_cast<bool>(out),"cannot open synthetic SURF.DAT");
    out<<"SURF.DAT        2.1             Hour Start and End Times with Seconds\n"
       <<"1\nG8 10km 2 station synthetic annual driver, no real observations\n"
       <<"NONE\nUTC+0000\n";
    stamp(out,begin);out<<" ";stamp(out,end,true);out<<" 2\n";
    out<<"58321\n58322\n";
    const int total=static_cast<int>(duration_cast<hours>(end-begin).count());
    for(int h=0;h<total;++h) {
        const auto now=begin+hours{h};
        stamp(out,now);out<<" ";stamp(out,now+hours{1},true);out<<"\n";
        const float ws1=3.f+static_cast<float>(h%7)*0.1f;
        const float ws2=4.f+static_cast<float>(h%11)*0.1f;
        const int wd1=90+(h%19),wd2=120+(h%13);
        out<<std::fixed<<std::setprecision(3)
           <<ws1<<" "<<wd1<<" 722 5 "
           <<283.f+float(h%24)*0.08f<<" 60 1013.000 0\n"
           <<ws2<<" "<<wd2<<" 722 5 "
           <<285.f+float(h%19)*0.06f<<" 65 1008.000 0\n";
    }
    require_test(static_cast<bool>(out),"write synthetic SURF.DAT failed");
}
static void level(std::ostream& out,float pressure,int z,float temperature,
                  int direction,int speed) {
    out<<"   "<<std::fixed<<std::setprecision(1)<<std::setw(6)<<pressure
       <<"/"<<std::setw(5)<<z
       <<"/"<<std::setw(5)<<temperature
       <<"/"<<std::setw(3)<<direction
       <<"/"<<std::setw(3)<<speed;
}
static void write_upper(const std::string& path,int id,sys_seconds begin,
                        sys_seconds end) {
    std::ofstream out(path);
    require_test(static_cast<bool>(out),"cannot open synthetic UP.DAT");
    out<<"UP.DAT          2.1             Hour Start and End Times with Seconds\n"
       <<"1\nG8 10km original READ62 formatted input fixture\nNONE\nUTC+0000\n";
    stamp(out,begin);out<<" ";stamp(out,end);out<<" 500.0 2 1\nF F F F\n";
    int index=0;
    for(auto when=begin-hours{12};when<=end+hours{12};when+=hours{12},++index) {
        const auto d=year_month_day{floor<days>(when)};
        const int hour=static_cast<int>(
            duration_cast<hours>(when-floor<days>(when)).count());
        out<<"6201 "<<id<<" "
           <<int(d.year())<<" "<<unsigned(d.month())<<" "<<unsigned(d.day())
           <<" "<<hour<<" 0 "
           <<int(d.year())<<" "<<unsigned(d.month())<<" "<<unsigned(d.day())
           <<" "<<hour<<" 0 2 2\n";
        const int direction=90+(id%5)+index%5;
        level(out,1000.0f,120,280.f,direction,5+index%4);
        level(out,500.f,5500,259.8f,direction,12+index%4);
        out<<"\n";
    }
    require_test(static_cast<bool>(out),"write synthetic UP.DAT failed");
}
static std::uint64_t digest(std::uint64_t value,float sample) {
    value^=std::bit_cast<std::uint32_t>(sample);
    return value*1099511628211ULL;
}
static void write_geo(const std::string& path,int nx,int ny) {
    std::ofstream out(path);
    require_test(static_cast<bool>(out),"cannot open synthetic G8 GEO.DAT");
    out<<"GEO.DAT         2.1             original GEO grid fixture\n"
       <<"1\nG8 UTM50N 10km input fixture\nUTM\n50N\nWGS-84\n"
       <<nx<<" "<<ny<<" 510.885 3531.269 10.000 10.000\nKM  M\n"
       <<"1 - land use custom categories\n"
       <<"14 50 55 - NLU/IWAT\n"
       <<"10 -20 20 30 40 51 54 55 60 61 62 70 80 90 - categories\n";
    for(int j=ny-1;j>=0;--j)
        for(int i=0;i<nx;++i)out<<"20"<<(i==nx-1?"\n":",");
    out<<"1 - terrain height factor\n";
    for(int j=ny-1;j>=0;--j)
        for(int i=0;i<nx;++i)
            out<<(100+250*i+150*j)<<(i==nx-1?"\n":",");
    for(int k=0;k<6;++k){
        out<<"2 - gridded property\n";
        for(int j=ny-1;j>=0;--j)
            for(int i=0;i<nx;++i)
                out<<(k==0?0.1:0.2)<<(i==nx-1?"\n":",");
    }
    require_test(static_cast<bool>(out),"G8 GEO.DAT fixture write incomplete");
}
static void exercise_period(sys_seconds begin,sys_seconds end,
                            int expected_hours,bool require_year_boundary,
                            int nx,int ny) {
    const std::string surface_file="p6g_g8_10km_surf.dat";
    const std::string upper1_file="p6g_g8_10km_upper1.dat";
    const std::string upper2_file="p6g_g8_10km_upper2.dat";
    const std::string geo_file="p6g_g8_10km_geo.dat";
    write_geo(geo_file,nx,ny);
    const auto geo=cteas::calmet::p6g::read_geo_dynamic(
        geo_file,{nx,ny,50,'N',510.885,3531.269,10.0});
    require_test(geo.nx==nx&&geo.ny==ny&&geo.grid_km==10.f&&
                 geo.landuse.size()==static_cast<std::size_t>(nx*ny)&&
                 geo.terrain_m.size()==static_cast<std::size_t>(nx*ny),
                 "G8 dynamic 10km READGE grid was not parsed");
    write_surface(surface_file,begin,end);
    write_upper(upper1_file,58424,begin,end);
    write_upper(upper2_file,58425,begin,end);
    const auto surface=read_surface_dynamic(surface_file,{58321,58322});
    const auto upper=read_upper_station_set(
        {upper1_file,upper2_file},{58424,58425});
    // Expand geographic station separation from 35km to 100km in the
    // 120km annual test, while keeping the short 60km case unchanged.
    std::ostringstream controls;
    controls << "! PMAP = UTM !\n"
             << "! DATUM = WGS-84 !\n"
             << "! IUTMZN = 50 !\n"
             << "! UTMHEM = N !\n"
             << "! NX = " << nx << " !\n"
             << "! NY = " << ny << " !\n"
             << "! NZ = 9 !\n"
             << "! DGRIDKM = 10.0 !\n"
             << "! XORIGKM = 510.885 !\n"
             << "! YORIGKM = 3531.269 !\n"
             << "! NSSTA = 2 !\n"
             << "! NUSTA = 2 !\n"
             << "! ZFACE = 0,20,40,80,160,320,640,1200,2000,3000 !\n"
             << "! IEXTRP = -4 !\n"
             << "! ICALM = 0 !\n"
             << "! IPROG = 0 !\n"
             << "! NOOBS = 0 !\n"
             << "! IFRADJ = 1 !\n"
             << "! ISLOPE = 1 !\n"
             << "! IOBR = 0 !\n"
             << "! LVARY = F !\n"
             << "! RMIN = 0.5 !\n"
             << "! RMAX1 = 150.0 !\n"
             << "! RMAX2 = 150.0 !\n"
             << "! RMAX3 = 150.0 !\n"
             << "! R1 = 50.0 !\n"
             << "! R2 = 80.0 !\n"
             << "! BIAS = 0,0,0,0,0,0,0,0,0 !\n"
             << "! NSMTH = 1,0,2,1,0,2,1,0,1 !\n"
             << "! NINTR2 = 99,99,99,99,99,99,99,99,99 !\n";
    const std::string deck_text=controls.str()+
        (nx>6 ? std::string(
            "! SS2 = 'S2' 58322 610.885 3631.269 0 10.0 !\n"
            "! US2 = 'U2' 58425 600.885 3621.269 0 !\n") :
            std::string(
            "! SS2 = 'S2' 58322 545.885 3566.269 0 10.0 !\n"
            "! US2 = 'U2' 58425 540.885 3561.269 0 !\n"))+
        "! SS1 = 'S1' 58321 515.885 3536.269 0 10.0 !\n"
        "! US1 = 'U1' 58424 520.885 3541.269 0 !\n";
    const auto deck=original_calmet_multi_station_deck(
        deck_text,510.885f,3531.269f,2,2);
    // G14B: the SAME on-disk original-format GEO/SURF/multi-UP sources
    // now create the accepted-stage dynamic hourly authority. No other
    // test-only input objects may be substituted by the case loader.
    const std::string deck_file="p6g_g14_10km_met.inp";
    {
        std::ofstream input(deck_file);
        require_test(static_cast<bool>(input),"cannot write G14 original met.inp station fixture");
        input<<deck_text;
        require_test(static_cast<bool>(input),"G14 met.inp station fixture write failed");
    }
    const auto file_backed=load_unified_multistation_case(
        {geo_file,surface_file,{upper1_file,upper2_file},deck_file,
         {nx,ny,50,'N',510.885,3531.269,10.0},2,2});
    require_test(file_backed.planned_hours()==static_cast<std::size_t>(expected_hours)&&
                 file_backed.grid().nx==nx&&file_backed.grid().ny==ny&&
                 file_backed.stations().surface.size()==2&&
                 file_backed.stations().upper.size()==2&&
                 file_backed.completed_hours()==0,
                 "G14B source-file-backed single hourly authority not initialized");
    const cteas::calmet::p6g::GeoGridSpec expected_grid{
        nx,ny,50,'N',510.885,3531.269,10.0};
    // Negative original-source gates: never use externally supplied grid
    // sizes or ZFACE values when met.inp advertises a different grid.
    auto wrong_nx=deck_text;
    const std::string nx_record="! NX = "+std::to_string(nx)+" !";
    const auto nx_offset=wrong_nx.find(nx_record);
    require_test(nx_offset!=std::string::npos,"G14B grid source fixture missing NX");
    wrong_nx.replace(nx_offset,nx_record.size(),
                     "! NX = "+std::to_string(nx+1)+" !");
    bool blocked=false;
    try{
        validate_original_calmet_deck_grid(wrong_nx,expected_grid,2,2);
    }catch(const std::invalid_argument&){blocked=true;}
    require_test(blocked,"G14B accepted inconsistent met.inp NX");
    auto wrong_zface=deck_text;
    const auto last_face=wrong_zface.find("2000,3000");
    require_test(last_face!=std::string::npos,"G14B original ZFACE fixture absent");
    wrong_zface.replace(last_face,9,"2000,2000");
    blocked=false;
    try{
        validate_original_calmet_deck_grid(wrong_zface,expected_grid,2,2);
    }catch(const std::invalid_argument&){blocked=true;}
    require_test(blocked,"G14B accepted nonmonotonic original ZFACE");

    const auto clock=bind_original_calmet_station_inputs(deck,surface,upper);
    require_test(clock.size()==static_cast<std::size_t>(expected_hours),
                 "year duration not present in G8 input chain");
    SelectedBridgeGrid grid{
        nx,ny,10.0f,geo.zone,geo.hemisphere,
        {0,20,40,80,160,320,640,1200,2000,3000},geo.landuse
    };
    grid.synthetic_identity_diagno_tail=false;
    grid.source_terrain_diagno_tail=true;
    grid.terrain=prepare_g11_terrain(geo,35.0f);
    require_test(file_backed.has_original_controls()&&
                 file_backed.original_controls().bias[0]==-1.f,
                 "G15 source-effective READCF BIAS missing from file-backed scheduler");
    // Single config authority is G14B's parsed original met.inp. No
    // second deck parsing or test-driver constants for WIND1/INTER2.
    grid.source_controls=file_backed.original_controls();
    grid.zface_m=grid.source_controls->zface_m;
    grid.smoothing_passes.assign(grid.source_controls->nsmth.begin(),
                                 grid.source_controls->nsmth.end());
    // Selected P6E P6G G12: observed SURF.DAT 2SS temperatures enter
    // source-matched SURFVAR. Solar and coefficients stay explicitly
    // synthetic, while original HEATFX computes the actual QH field.
    // GAMMA is still an EXTERNAL synthetic input, never claimed as CGAMMA.
    auto hour_thermo=[&](std::size_t time){
        G12ExplicitSolarHeat forcing;
        forcing.end=surface.hourly.at(time).end;
        forcing.synthetic_radiation_fixture=true;
        forcing.irad=1;forcing.numts=2;forcing.trad_grid=20.f;
        forcing.isurft=-1;
        forcing.domain_temperature_k=285.f;
        forcing.critfn=10.f;
        forcing.coefficients=G12HeatCoefficients{
            950.f,0.f,-0.2f,1.f,0.f,0.f,1.f};
        const auto plane=static_cast<std::size_t>(nx*ny);
        const auto model_clock=static_cast<int>(time%24);
        forcing.sun_sine.assign(
            plane,model_clock>=6&&model_clock<18?0.9f:-0.2f);
        forcing.nearest_surface.reserve(plane);
        for(int j=0;j<ny;++j)for(int i=0;i<nx;++i)
            forcing.nearest_surface.push_back(i<nx/2?1:2);
        forcing.lapse_k_per_m.assign(plane,0.002f);
        forcing.initial_water_qh_wm2.assign(plane,0.f);
        return source_selected_g12_thermal_hour(
            deck,surface,surface.hourly.at(time),geo,forcing);
    };
    // G17B original-format FILE-BACKED smoke: the same GEO/SURF/UP
    // created above and accepted by G14B now feeds actual COORDLIB/UTC
    // SOLAR -> observed SURFVAR -> native HEATFX. The heat ancillaries
    // stay explicit fixture-only, so no production P6E state is claimed.
    G17BExplicitAncillaryFixture solar_inputs;
    solar_inputs.explicitly_test_only=true;
    solar_inputs.irad=1;solar_inputs.numts=2;solar_inputs.trad_grid=20.f;
    solar_inputs.coefficients={990.f,-30.f,-0.75f,3.4f,0.f,0.f,1.f};
    solar_inputs.isurft=-1;
    solar_inputs.domain_temperature_k=285.f;
    solar_inputs.critfn=10.f;
    const auto cells=static_cast<std::size_t>(nx*ny);
    // Not source physical input: assert the file-loaded station geometry
    // reproduces SETCOM's 1-based NEARS exactly, even across the annual case.
    solar_inputs.nearest_surface=source_setcom_nears(geo,deck);
    solar_inputs.initial_water_qh_wm2.assign(cells,0.f);
    solar_inputs.lapse_k_per_m.assign(cells,0.002f);
    const auto midnight=observed_solar_heat_selected(
        geo,deck,surface,surface.hourly.at(0),solar_inputs);
    const auto daytime=observed_solar_heat_selected(
        geo,deck,surface,surface.hourly.at(4),solar_inputs);
    require_test(midnight.sun_sine.size()==cells&&
                 daytime.sun_sine.size()==cells&&
                 daytime.observed.temp2d_k.size()==cells&&
                 daytime.sensible_heat_wm2.size()==cells,
                 "G17B real parsed-source GEO/SURF solar/TEMP2D/QH incomplete");
    const auto center=cells/2;
    require_test(midnight.sun_sine[center]<daytime.sun_sine[center]&&
                 midnight.shortwave_wm2[center]<daytime.shortwave_wm2[center],
                 "G17B original-format source solar did not follow UTC hour");
    require_test(daytime.fradj_fixture.temperature_k==
                     daytime.slope_fixture.temperature_k&&
                 daytime.slope_fixture.sensible_heat_w_m2==
                     daytime.sensible_heat_wm2,
                 "G17B file-backed thermal result cannot be staged into G17");
    // 6x6 (60 km) short cross-year; expanded 12x12 (120 km) annual.
    require_test(grid.nx*grid.ny==nx*ny&&grid.spacing_km==10.f,
                 "G8 must test precisely 10km cells");
    const std::vector<float> zface(
        grid.zface_m.begin(),grid.zface_m.end());
    const auto prepared=prepare_upper_original_selected(upper,zface);
    // Stage-gate negative controls run once per scenario: no invisible tail
    // when disabled, and no physical computation with malformed smoothing.
    {
        auto no_tail=grid;
        no_tail.synthetic_identity_diagno_tail=false;
        no_tail.source_terrain_diagno_tail=false;
        no_tail.terrain.reset();
        no_tail.smoothing_passes.clear();
        const auto first=selected_multisite_hour(
            deck,surface.hourly.front(),clock.front(),prepared,no_tail);
        require_test(!first.selected_tail_exercised&&first.nonzero_w_faces==0,
                     "G10 DIAGNO tail must be opt-in, never silently inferred");
        auto malformed=grid;
        auto first_result=hour_thermo(0);
        auto first_thermal=first_result.thermal;
        malformed.smoothing_passes.pop_back();
        bool denied=false;
        try {
            (void)selected_multisite_hour(
                deck,surface.hourly.front(),clock.front(),prepared,malformed,&first_thermal);
        }catch(const std::invalid_argument&){denied=true;}
        require_test(denied,
                     "G10 short/missing SMOOTH pass vector accepted");
        malformed=grid;
        malformed.smoothing_passes[0]=-1;
        denied=false;
        try {
            (void)selected_multisite_hour(
                deck,surface.hourly.front(),clock.front(),prepared,malformed,&first_thermal);
        }catch(const std::invalid_argument&){denied=true;}
        require_test(denied,"G10 negative SMOOTH pass count accepted");
        denied=false;
        try {
            (void)selected_multisite_hour(
                deck,surface.hourly.front(),clock.front(),prepared,grid);
        }catch(const std::invalid_argument&){denied=true;}
        require_test(denied,"G11 terrain silently accepted without hourly thermal provider");
        malformed=grid;
        malformed.synthetic_identity_diagno_tail=true;
        denied=false;
        try {
            (void)selected_multisite_hour(
                deck,surface.hourly.front(),clock.front(),prepared,malformed,
                &first_thermal);
        }catch(const std::invalid_argument&){denied=true;}
        require_test(denied,"G11 contradictory identity/terrain modes accepted");
        auto shifted=hour_thermo(0).thermal;
        shifted.end+=hours{1};
        denied=false;
        try {
            (void)selected_multisite_hour(
                deck,surface.hourly.front(),clock.front(),prepared,grid,
                &shifted);
        }catch(const std::invalid_argument&){denied=true;}
        require_test(denied,
                     "G11 accepted thermal fields from next UTC hour");
    }
    std::uint64_t hash=1469598103934665603ULL;
    bool varied=false, crossed=false;
    float first_u=0.f;
    auto last=begin;
    std::size_t total_contributions=0;
    std::size_t total_fradj_changed=0,total_slope_changed=0;
    float first_temp=0.f,first_qh=0.f;
    bool varied_observed_temp=false,varied_computed_qh=false;
    for(std::size_t hour=0;hour<clock.size();++hour) {
        const auto& input=clock[hour];
        require_test(input.end==begin+hours{static_cast<int>(hour)+1},
                     "G8 one-hour input clock drifted");
        const auto computed=hour_thermo(hour);
        const auto& thermal=computed.thermal;
        require_test(thermal.end==input.end&&
                     thermal.provenance==
                         TerrainHourProvenance::ObservedSurfvarSyntheticSolarFixture&&
                     thermal.temperature_k.size()==
                         static_cast<std::size_t>(nx*ny),
                     "G12 source SURFVAR→HEATFX thermal input missing");
        if(hour==0){
            first_temp=thermal.temperature_k.front();
            first_qh=thermal.sensible_heat_w_m2.front();
        }else{
            varied_observed_temp|=thermal.temperature_k.front()!=first_temp;
            varied_computed_qh|=thermal.sensible_heat_w_m2.front()!=first_qh;
        }
        const auto output=selected_multisite_hour(
            deck,surface.hourly[hour],input,prepared,grid,&thermal);
        require_test(output.end==input.end,
                     "G10 source-selected DIAGNO returned wrong hour");
        require_test(output.original_terrain_kernels_exercised,
                     "G11 FRADJ/SLOPE not executed");
        total_fradj_changed+=output.fradj_changed_cells;
        total_slope_changed+=output.slope_changed_cells;
        require_test(output.selected_tail_exercised&&
                     output.nonzero_w_faces>0&&
                     std::isfinite(output.top_center_w_mps),
                     "G10 10km selected SMOOTH/DIVCEL/W was not evaluated");
        if(hour==0)first_u=output.center_u_mps;
        if(hour>0 && output.center_u_mps!=first_u)varied=true;
        if(year_month_day{floor<days>(output.end)}.year()!=
           year_month_day{floor<days>(last)}.year())
            crossed=true;
        last=output.end;
        total_contributions+=output.observed_contributions;
        hash=digest(hash,thermal.temperature_k.front());
        hash=digest(hash,thermal.sensible_heat_w_m2.front());
        hash=digest(hash,output.firstguess_center_u_mps);
        hash=digest(hash,output.firstguess_center_v_mps);
        hash=digest(hash,output.center_u_mps);
        hash=digest(hash,output.center_v_mps);
        hash=digest(hash,output.upper_u_mps);
        hash=digest(hash,output.upper_v_mps);
        hash=digest(hash,output.final_center_u_mps);
        hash=digest(hash,output.final_center_v_mps);
        hash=digest(hash,output.top_center_w_mps);
    }
    require_test(varied&&total_contributions>static_cast<std::size_t>(expected_hours),
                 "G8 selected multi-observation fields not active/variable");
    require_test(!require_year_boundary||crossed,
                 "G8 did not exercise Gregorian year boundary");
    require_test(varied_observed_temp&&varied_computed_qh,
                 "G12 SOURCE SURFVAR or HEATFX did not respond to dynamic station/hour data");
    require_test(total_slope_changed>0,
                 "G11 nonflat source GEO and negative sensible heat did not produce slope flow");
    require_test(hash!=1469598103934665603ULL,"G11 digest unchanged");
    std::cout<<"G12_10KM_SURFVAR_HEATFX_TERRAIN_DIAGNO_TAIL hours="<<expected_hours
             <<" grid="<<nx<<"x"<<ny<<"x9 spacing_km=10 surface=2 upper=2"
             <<" contributions="<<total_contributions
             <<" fradj_changed="<<total_fradj_changed
             <<" slope_changed="<<total_slope_changed
             <<" signature="<<std::hex<<hash<<std::dec<<"\n";
    std::remove(surface_file.c_str());
    std::remove(upper1_file.c_str());
    std::remove(upper2_file.c_str());
    std::remove(geo_file.c_str());
    std::remove("p6g_g14_10km_met.inp");
}
int main(){
    try{
        // Dec 2023 to Jan 2024 verifies leap-year transition and
        // both two-station readers with the original hour-24 record encoding.
        const auto cross=sys_days{year{2023}/December/31};
        exercise_period(cross,cross+hours{48},48,true,6,6);
        // 2024 is a leap year: actual 8784 consecutive UTC hours.
        const auto annual=sys_days{year{2024}/January/1};
        exercise_period(annual,annual+hours{8784},8784,true,12,12);
        std::cout<<"PASS P6G_G12_10KM_MULTISTATION_P6E_SURFVAR_HEATFX_TO_DIAGNO_8784H\n";
        return 0;
    }catch(const std::exception& e){
        std::cerr<<"P6G_G8_10KM_FAIL "<<e.what()<<"\n";
        return 1;
    }
}
