#pragma once

#include <cstdint>
#include <limits>
#include <type_traits>

namespace cteas::puff {

// ABI contract for ORIGINAL CALPUFF 7.2.1 L150618 compiled with the exact
// flags in reference/build_original_calpuff.py. Do not turn the whole model
// into float OR double: unqualified Fortran REAL uses 4-byte storage;
// explicitly declared DOUBLE PRECISION / REAL*8 uses 8 bytes; the default
// INTEGER in /PUFF/ and /PT1/ uses 4 bytes. An individual Fortran declaration
// overrides these aliases; audit it before selecting a ported field's type.
using VendorDefaultReal = float;
using VendorExplicitDouble = double;
using VendorDefaultInteger = std::int32_t;

// /PT1/ XPT1GRD/YPT1GRD, /PUFF/ XPB/YPB/ZPB and QSTAK/QM/QU are
// unqualified REAL in the original included COMMON blocks.
using VendorPointCommonReal = VendorDefaultReal;
using VendorPuffCommonReal = VendorDefaultReal;

static_assert(sizeof(VendorDefaultReal) == 4 && sizeof(VendorExplicitDouble) == 8);
static_assert(sizeof(VendorDefaultInteger) == 4);
static_assert(std::numeric_limits<VendorDefaultReal>::is_iec559);
static_assert(std::numeric_limits<VendorExplicitDouble>::is_iec559);
static_assert(std::is_same_v<VendorPointCommonReal, float> &&
              std::is_same_v<VendorPuffCommonReal, float>);

// Text/float boundary: read original control REAL values as single precision
// before calculating the vendor relative grid locations. Do not round the
// GIS lon/lat result in place of the independently rounded puff.inp text.
[[nodiscard]] inline VendorDefaultReal original_real_from_text(double value) noexcept {
    return static_cast<VendorDefaultReal>(value);
}

// COMP original L10342/L10447/L10563/L10569:
 //   TAVGI = 1.0 / TAVG   (unqualified Fortran REAL*4)
 //   TFRACT = TSAMP * TAVGI
 // CALCPF L4302 then evaluates XTEMP = F1 * TFRACT.
 // A single TSAMP/TAVG division is NOT bitwise equivalent: hour 2 native
 // DGM seq1607 receptor (25,28) differs by exactly one binary32 ULP.
[[nodiscard]] inline VendorDefaultReal original_calcpf_time_fraction(
    VendorDefaultReal tsamp,VendorDefaultReal averaging_seconds) noexcept {
    const VendorDefaultReal tavgi=1.0F/averaging_seconds;
    return tsamp*tavgi;
}

} // namespace cteas::puff
