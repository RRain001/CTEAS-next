#pragma once
#include "cteas/puff/calmet21.hpp"
#include <cstdint>
#include <functional>
#include <string>
#include <vector>

namespace cteas::puff {
// Original METFM=1 CALMET hour. 3D arrays are z-major, y-major,
// x-fastest; each 2D field is y-major/x-fastest, stored as REAL*4.
struct OriginalMetHour {
    Calmet21Time begin,end;
    int nx=0,ny=0,nz=0;
    std::vector<float> u,v,w,t;
    std::vector<float> ustar,zi,el,wstar,tempk,rho,qsw;
    std::vector<std::int32_t> ipgt,irh;
    // Byte-for-byte digest of original 45 field payloads in Fortran OUTHR
    // order. This checks INPUT only; GETCELL/ADVECT are NOT implemented here.
    [[nodiscard]] std::uint64_t original_field_fingerprint() const;
};
class OriginalMetHourlyReader {
public:
    using Observer=std::function<void(const Calmet21Header&,
        const Calmet21Static&,const OriginalMetHour&)>;
    // Bounded to one assembled hour. Callback receives a borrowed snapshot.
    // Does not interpolate winds or run COMP.
    static Calmet21Summary read(const std::string& path, const Observer& callback,
                                bool frozen_hefei_2022=false);
};
} // namespace cteas::puff
