#pragma once
// G18C6: selected-only, reference-independent P6F CALMET.DAT 2.1 dataset
// built from G18C5 native 45-record candidates, source GEO + met.inp ZFACE,
// source-ordered SS/US and literal hour clocks. Uses frozen P6F serializer,
// not a second custom Fortran binary writer. This is NOT 17-stage G14
// production parity or acceptance of multi-site original CALMET physics.
#include "cteas/p6/p6g_g18c5_selected_p6f_fields.hpp"
#include "cteas/p6f/calmet_dat21_writer.hpp"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <stdexcept>
#include <string>
#include <vector>

namespace cteas::calmet::p6g {

inline cteas::p6f::Calmet21File g18c6_selected_one_hour_dataset(
    const MultiHourFrame& frame,
    const G18C5SelectedHourFields& selected,
    const std::vector<int>& original_nears,
    const std::string& original_deck,
    bool explicitly_test_only,
    bool allow_one_one_source_audit=false,
    bool allow_asymmetric_source_audit=false) {
    using namespace std::chrono;
    const auto nx=static_cast<std::size_t>(frame.grid.nx);
    const auto ny=static_cast<std::size_t>(frame.grid.ny);
    const auto n=nx*ny;
    if(!explicitly_test_only||!frame.source_controls||
       nx<2||ny<2||nx>400||ny>400||
       frame.input.end!=selected.end||
       frame.surface.end!=selected.end||
       frame.surface.end-frame.surface.start!=hours{1}||
       ((frame.stations.surface.size()<2||frame.stations.upper.size()<2)&&
        !((allow_one_one_source_audit&&frame.stations.surface.size()==1&&
           frame.stations.upper.size()==1)||
          (allow_asymmetric_source_audit&&
           ((frame.stations.surface.size()==1&&frame.stations.upper.size()>=2&&
             frame.stations.upper.size()>=2)||
            (frame.stations.surface.size()>=2&&frame.stations.surface.size()>=2&&
             frame.stations.upper.size()==1)))))||
       frame.grid.nlu<=0||frame.grid.nlu>200||
       frame.grid.valid_categories.size()!=
           static_cast<std::size_t>(frame.grid.nlu)||
       frame.grid.landuse.size()!=n||frame.grid.z0_m.size()!=n||
       frame.grid.terrain_m.size()!=n||frame.grid.lai.size()!=n||
       original_nears.size()!=n||
       selected.station_ids.size()!=frame.stations.surface.size()||
       selected.real.size()!=43||selected.integer.size()!=2||
       !std::isfinite(frame.grid.grid_km)||frame.grid.grid_km<=0.f||
       !std::isfinite(frame.grid.xorigin_km)||
       !std::isfinite(frame.grid.yorigin_km))
        throw std::invalid_argument("G18C6 incomplete original GEO, station and native P6F source");
    if(g18c1_source_integer(original_deck,"IRTYPE")!=1||
       g18c1_source_integer(original_deck,"IWFCOD")!=1||
       g18c1_source_integer(original_deck,"IFORMO")!=1||
       g18c1_source_integer(original_deck,"IUTMZN")!=frame.grid.zone||
       source_wind_normalize(source_wind_value(original_deck,"UTMHEM"))!=
           std::string(1,frame.grid.hemisphere)||
       source_wind_normalize(source_wind_value(original_deck,"LCALGRD"))!="T"||
       g18c1_source_integer(original_deck,"NPSTA")!=0)
        throw std::invalid_argument("G18C6 unsupported original P6F output mode / CRS");
    // NEARS is a source-derived static field, not merely any in-range
    // station index; reject a fabricated but valid ordinal distribution.
    if(original_nears!=source_setcom_nears(frame.grid,frame.stations))
        throw std::invalid_argument("G18C6 NEARS differs from original SETCOM geometry");
    const auto matched_controls=parse_original_wind_controls(original_deck);
    if(matched_controls.zface_m!=frame.source_controls->zface_m)
        throw std::invalid_argument("G18C6 original ZFACE does not belong to source deck");
    cteas::p6f::Calmet21File out;
    auto& header=out.header;
    const auto begin_seconds=frame.surface.start.time_since_epoch().count();
    const auto end_seconds=frame.surface.end.time_since_epoch().count();
    const auto start=cteas::p6f::calendar_from_instant(begin_seconds);
    const auto finish=cteas::p6f::calendar_from_instant(end_seconds);
    if(start.minute!=0||start.second!=0||
       finish.minute!=0||finish.second!=0)
        throw std::invalid_argument("G18C6 source hour must align to UTC clock");
    header.begin_year=start.year;header.begin_month=start.month;
    header.begin_day=start.day;header.begin_hour=start.hour;header.begin_second=0;
    header.end_year=finish.year;header.end_month=finish.month;
    header.end_day=finish.day;header.end_hour=finish.hour;header.end_second=0;
    header.comments={
        "P6G G18C6 test-only 45-record source candidate; not accepted multi-SS physics",
        "Source statics: dynamic GEO.DAT/met.inp and original SS/US; no MET.DAT backfill",
        "Scientific verification pending G14 17-stage and vendor 45-field numerical gate"};
    header.timezone="UTC+0000";
    header.irlg=1;header.irtype=1;
    header.nx=frame.grid.nx;header.ny=frame.grid.ny;header.nz=9;
    header.dgrid_m=frame.grid.grid_km*1000.f;
    header.xorigin_m=frame.grid.xorigin_km*1000.f;
    header.yorigin_m=frame.grid.yorigin_km*1000.f;
    header.iwfcod=1;
    header.nssta=static_cast<std::int32_t>(frame.stations.surface.size());
    header.nusta=static_cast<std::int32_t>(frame.stations.upper.size());
    header.npsta=0;header.nowsta=0;
    header.nlu=frame.grid.nlu;
    header.iwat1=frame.grid.iwat1;
    header.iwat2=frame.grid.iwat2;
    header.lcalgrd=true;
    header.projection.pmap="UTM";
    header.projection.datum="WGS-84";
    header.projection.daten="02-21-2003";
    header.projection.utmhem=std::string(1,frame.grid.hemisphere);
    header.projection.iutmzn=frame.grid.zone;
    auto& statics=out.statics;
    statics.zface_m.assign(frame.source_controls->zface_m.begin(),
                           frame.source_controls->zface_m.end());
    for(std::size_t k=0;k<frame.stations.surface.size();++k) {
        const auto& site=frame.stations.surface[k];
        if(site.id!=selected.station_ids[k]||
           !std::isfinite(site.local_x_m)||!std::isfinite(site.local_y_m))
            throw std::invalid_argument("G18C6 incorrect SURF native station order");
        statics.surface_x_m.push_back(site.local_x_m);
        statics.surface_y_m.push_back(site.local_y_m);
    }
    for(const auto& site:frame.stations.upper) {
        if(site.id<=0||!std::isfinite(site.local_x_m)||
           !std::isfinite(site.local_y_m))
            throw std::invalid_argument("G18C6 invalid upper source UTM site");
        statics.upper_x_m.push_back(site.local_x_m);
        statics.upper_y_m.push_back(site.local_y_m);
    }
    statics.z0_m=frame.grid.z0_m;
    statics.elev_m=frame.grid.terrain_m;
    statics.xlai=frame.grid.lai;
    for(std::size_t k=0;k<n;++k) {
        const int land=frame.grid.landuse[k];
        if(std::find(frame.grid.valid_categories.begin(),
                     frame.grid.valid_categories.end(),land)==
                     frame.grid.valid_categories.end()||
           !std::isfinite(statics.z0_m[k])||statics.z0_m[k]<=0.f||
           !std::isfinite(statics.elev_m[k])||
           !std::isfinite(statics.xlai[k])||
           original_nears[k]<1||
           original_nears[k]>header.nssta)
            throw std::invalid_argument("G18C6 invalid original GEO/NEARS physical static");
        statics.ilandu.push_back(static_cast<std::int32_t>(land));
        statics.nears.push_back(static_cast<std::int32_t>(original_nears[k]));
    }
    // P6F's immutable hourly_labels is the sole authoritative order;
    // there must be exactly 45 native-produced values, no values borrowed
    // from an existing original CALMET.DAT file or frozen reference.
    const auto labels=cteas::p6f::hourly_labels(9,1,true,0);
    if(labels.size()!=45)
        throw std::logic_error("G18C6 original OUTHR 45-record contract changed");
    auto field_begin=cteas::p6f::instant_to_time(begin_seconds);
    auto field_end=field_begin;
    field_end.seconds+=3600;
    for(const auto& label:labels) {
        cteas::p6f::Calmet21Field field;
        field.label=label;field.begin=field_begin;field.end=field_end;
        field.integer=cteas::p6f::is_integer_label(label);
        if(field.integer) {
            const auto found=selected.integer.find(label);
            if(found==selected.integer.end()||found->second.size()!=n)
                throw std::invalid_argument("G18C6 original integer field missing");
            field.integer_values=found->second;
        }else{
            const auto found=selected.real.find(label);
            if(found==selected.real.end()||found->second.size()!=n)
                throw std::invalid_argument("G18C6 original real field missing");
            field.real_values=found->second;
        }
        out.hourly.push_back(std::move(field));
    }
    cteas::p6f::validate_calmet_dat21(out);
    return out;
}

} // namespace cteas::calmet::p6g
