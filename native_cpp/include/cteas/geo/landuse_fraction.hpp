#pragma once
#include <cstddef>
#include <cstdint>
#include <vector>
#include "cteas/geo/source_inputs.hpp"
namespace cteas::reconstruction::geo {
struct P2Grid { double x0_m{},y0_m{},dx_m{}; std::size_t nx{},ny{}; };
struct P2Fractions {
  P2Grid grid;
  std::vector<int> categories;
  std::vector<std::uint32_t> counts; // ((j*nx+i)*nclass+k)
  std::vector<std::uint32_t> cell_samples;
  std::size_t included{},outside{};
  [[nodiscard]] double fraction(std::size_t i,std::size_t j,std::size_t k) const;
};
[[nodiscard]] P2Fractions compute_generic_utm50n(const GenericLanduse&,P2Grid);
} // namespace cteas::reconstruction::geo
