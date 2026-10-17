#include "cteas/geo/grid_origin.hpp"
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <string>

using cteas::reconstruction::geo::three_decimal_origin_km;
using cteas::reconstruction::geo::require_frozen_hefei_origin_km;

void check_refused(const std::string& text) {
    try {(void)three_decimal_origin_km(text);}
    catch(const std::invalid_argument& error) {
        if(std::string(error.what()).find("GRID_ORIGIN_PRECISION")!=std::string::npos)
            return;
        throw;
    }
    throw std::runtime_error("higher-precision or malformed grid origin was accepted: "+text);
}
int main() {
    if(std::fabs(three_decimal_origin_km("510.885")-510.885)>1e-12)
        throw std::runtime_error("canonical easting changed");
    if(std::fabs(three_decimal_origin_km("3531.269")-3531.269)>1e-12)
        throw std::runtime_error("canonical northing changed");
    // Non-Hefei coordinates may use the same universal three-decimal
    // syntax in future independently approved case profiles.
    if(std::fabs(three_decimal_origin_km("123.456")-123.456)>1e-12)
        throw std::runtime_error("future three-decimal coordinate rejected");
    require_frozen_hefei_origin_km("510.885","3531.269");
    for(const auto& bad : {"510.8846439571007","3531.2689269678035","510.8850",
                          "3531.269000","510.88","510","NaN","inf","1e3"," 510.885","510.885 "})
        check_refused(bad);
    bool mismatch=false;
    try {require_frozen_hefei_origin_km("510.886","3531.269");}
    catch(const std::invalid_argument& e) {
        mismatch=std::string(e.what()).find("GRID_ORIGIN_CASE_MISMATCH")!=std::string::npos;
    }
    if(!mismatch)throw std::runtime_error("wrong selected-case origin accepted");
    std::cout<<"GRID_ORIGIN_PRECISION_THREE_DECIMAL_KM=PASS\n";
}
