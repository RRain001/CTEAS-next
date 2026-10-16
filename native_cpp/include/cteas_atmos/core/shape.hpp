#pragma once

#include <concepts>
#include <cstddef>
#include <limits>
#include <stdexcept>
#include <string>
#include <type_traits>

namespace cteas::atmos {

namespace detail {

template <std::integral Integer>
[[nodiscard]] std::size_t checked_positive_extent(
    Integer value,
    const char* name) {
  using Value = std::remove_cv_t<Integer>;

  if constexpr (std::same_as<Value, bool>) {
    throw std::invalid_argument(std::string{name} +
                                " must be a positive integer extent");
  } else {
    if constexpr (std::signed_integral<Value>) {
      if (value <= 0) {
        throw std::invalid_argument(std::string{name} +
                                    " must be greater than zero");
      }
    } else if (value == 0) {
      throw std::invalid_argument(std::string{name} +
                                  " must be greater than zero");
    }

    using Unsigned = std::make_unsigned_t<Value>;
    const auto unsigned_value = static_cast<Unsigned>(value);
    if constexpr (sizeof(Unsigned) > sizeof(std::size_t)) {
      if (unsigned_value >
          static_cast<Unsigned>(std::numeric_limits<std::size_t>::max())) {
        throw std::overflow_error(std::string{name} +
                                  " does not fit in std::size_t");
      }
    }
    return static_cast<std::size_t>(unsigned_value);
  }
}

[[nodiscard]] inline std::size_t checked_multiply(
    std::size_t left,
    std::size_t right,
    const char* context) {
  if (left != 0 && right > std::numeric_limits<std::size_t>::max() / left) {
    throw std::overflow_error(std::string{context} + " size overflows");
  }
  return left * right;
}

[[nodiscard]] inline std::size_t checked_add_one(
    std::size_t value,
    const char* context) {
  if (value == std::numeric_limits<std::size_t>::max()) {
    throw std::overflow_error(std::string{context} + " extent overflows");
  }
  return value + 1;
}

}  // namespace detail

class Shape2D {
 public:
  template <std::integral X, std::integral Y>
  explicit Shape2D(X nx, Y ny)
      : nx_(detail::checked_positive_extent(nx, "nx")),
        ny_(detail::checked_positive_extent(ny, "ny")),
        size_(detail::checked_multiply(nx_, ny_, "Shape2D")) {}

  [[nodiscard]] std::size_t nx() const noexcept { return nx_; }
  [[nodiscard]] std::size_t ny() const noexcept { return ny_; }
  [[nodiscard]] std::size_t size() const noexcept { return size_; }

  [[nodiscard]] bool operator==(const Shape2D&) const noexcept = default;

 private:
  std::size_t nx_;
  std::size_t ny_;
  std::size_t size_;
};

class Shape3D {
 public:
  template <std::integral X, std::integral Y, std::integral Z>
  explicit Shape3D(X nx, Y ny, Z nz)
      : nx_(detail::checked_positive_extent(nx, "nx")),
        ny_(detail::checked_positive_extent(ny, "ny")),
        nz_(detail::checked_positive_extent(nz, "nz")),
        horizontal_size_(
            detail::checked_multiply(nx_, ny_, "Shape3D horizontal")),
        size_(detail::checked_multiply(
            horizontal_size_, nz_, "Shape3D total")) {}

  [[nodiscard]] std::size_t nx() const noexcept { return nx_; }
  [[nodiscard]] std::size_t ny() const noexcept { return ny_; }
  [[nodiscard]] std::size_t nz() const noexcept { return nz_; }
  [[nodiscard]] std::size_t horizontal_size() const noexcept {
    return horizontal_size_;
  }
  [[nodiscard]] std::size_t size() const noexcept { return size_; }

  [[nodiscard]] bool operator==(const Shape3D&) const noexcept = default;

 private:
  std::size_t nx_;
  std::size_t ny_;
  std::size_t nz_;
  std::size_t horizontal_size_;
  std::size_t size_;
};

}  // namespace cteas::atmos
