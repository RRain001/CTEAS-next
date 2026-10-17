#pragma once

#include <stdexcept>
#include <string_view>

namespace cteas::atmos {

enum class CanonicalUnit {
  dimensionless,
  metre,
  second,
  metre_per_second,
  per_second,
  square_metre_per_second,
  kelvin,
  kelvin_per_metre,
  pascal,
  degree,
  kilogram_per_cubic_metre,
  becquerel,
  becquerel_per_cubic_metre,
  becquerel_per_square_metre,
  becquerel_per_square_metre_per_second,
  millimetre,
  watt_per_square_metre,
};

[[nodiscard]] inline bool is_known_canonical_unit(
    CanonicalUnit unit) noexcept {
  switch (unit) {
    case CanonicalUnit::dimensionless:
    case CanonicalUnit::metre:
    case CanonicalUnit::second:
    case CanonicalUnit::metre_per_second:
    case CanonicalUnit::per_second:
    case CanonicalUnit::square_metre_per_second:
    case CanonicalUnit::kelvin:
    case CanonicalUnit::kelvin_per_metre:
    case CanonicalUnit::watt_per_square_metre:
    case CanonicalUnit::pascal:
    case CanonicalUnit::degree:
    case CanonicalUnit::kilogram_per_cubic_metre:
    case CanonicalUnit::becquerel:
    case CanonicalUnit::becquerel_per_cubic_metre:
    case CanonicalUnit::becquerel_per_square_metre:
    case CanonicalUnit::becquerel_per_square_metre_per_second:
    case CanonicalUnit::millimetre:
      return true;
  }
  return false;
}

[[nodiscard]] inline std::string_view canonical_symbol(CanonicalUnit unit) {
  switch (unit) {
    case CanonicalUnit::dimensionless:
      return "1";
    case CanonicalUnit::metre:
      return "m";
    case CanonicalUnit::second:
      return "s";
    case CanonicalUnit::metre_per_second:
      return "m s-1";
    case CanonicalUnit::per_second:
      return "s-1";
    case CanonicalUnit::square_metre_per_second:
      return "m2 s-1";
    case CanonicalUnit::kelvin:
      return "K";
    case CanonicalUnit::kelvin_per_metre:
      return "K m-1";
    case CanonicalUnit::watt_per_square_metre:
      return "W m-2";
    case CanonicalUnit::pascal:
      return "Pa";
    case CanonicalUnit::degree:
      return "degree";
    case CanonicalUnit::kilogram_per_cubic_metre:
      return "kg m-3";
    case CanonicalUnit::becquerel:
      return "Bq";
    case CanonicalUnit::becquerel_per_cubic_metre:
      return "Bq m-3";
    case CanonicalUnit::becquerel_per_square_metre:
      return "Bq m-2";
    case CanonicalUnit::becquerel_per_square_metre_per_second:
      return "Bq m-2 s-1";
    case CanonicalUnit::millimetre:
      return "mm";
  }
  throw std::invalid_argument("unknown CanonicalUnit value");
}

}  // namespace cteas::atmos
