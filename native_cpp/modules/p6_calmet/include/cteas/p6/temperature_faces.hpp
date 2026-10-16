#pragma once
// Original CALMET FACET -> INTP (calmet.for L6929-6982, L9122-9214).
// Selected 2022 P4 profiles: interpolate sounding T(K) to 10 model faces,
// preserving Fortran first-valid-above and last-valid-below priority, while
// refusing nonphysical extrapolation outside the original INTP's domain.
#include "cteas/p6/read_upper.hpp"
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <vector>
namespace cteas::calmet::p6 {
inline float calmet_intp_temperature(
        const UpperSounding& s,float height_m) {
    if(!std::isfinite(height_m)||s.data.size()<2)
        throw std::invalid_argument("INTP invalid temperature query");
    constexpr float missing=999.9f-0.01f;
    std::size_t upper=s.data.size();
    for(std::size_t j=1;j<s.data.size();++j) {
        if(s.data[j].height_lgl_m>=height_m &&
           s.data[j].temperature_k<missing){
            upper=j;break;
        }
    }
    if(upper==s.data.size())
        throw std::invalid_argument("INTP no valid temperature at or above model face");
    std::size_t lower=s.data.size();
    for(std::size_t j=upper;j-->0;){
        if(s.data[j].temperature_k<missing){
            lower=j;break;
        }
    }
    if(lower==s.data.size()||s.data[lower].height_lgl_m>height_m)
        throw std::invalid_argument("INTP no valid temperature below face");
    const float delta=s.data[upper].height_lgl_m-
                      s.data[lower].height_lgl_m;
    if(std::abs(delta)<1.0e-5f)
        return 0.5f*(s.data[upper].temperature_k+
                     s.data[lower].temperature_k);
    const float ratio=(s.data[upper].height_lgl_m-height_m)/delta;
    return s.data[upper].temperature_k-
        (s.data[upper].temperature_k-s.data[lower].temperature_k)*ratio;
}
inline std::vector<float> calmet_facet_temperatures(
        const UpperSounding& s,const std::vector<float>& zfaces) {
    if(zfaces.size()<2||zfaces.size()>13)
        throw std::invalid_argument("FACET invalid 3D model-layer count");
    std::vector<float> out;
    out.reserve(zfaces.size());
    float prior=-1.0f;
    for(float height:zfaces){
        if(!std::isfinite(height)||height<0||height<=prior)
            throw std::invalid_argument("FACET nonmonotonic height or nonfinite");
        prior=height;
        out.push_back(calmet_intp_temperature(s,height));
    }
    return out;
}
} // namespace cteas::calmet::p6
