#pragma once

#include <cstddef>
#include <span>
#include <stdexcept>
#include <type_traits>
#include <utility>
#include <vector>

#include "cteas_atmos/core/shape.hpp"

namespace cteas::atmos {

// Array2D and Array3D are numerical storage primitives. They do not provide
// the per-element validity, units, time meaning, location metadata, or
// provenance required of a complete formal scientific field.

template <typename T>
class Array2D {
  static_assert(std::is_object_v<T>);
  static_assert(!std::is_const_v<T> && !std::is_volatile_v<T>);
  static_assert(!std::is_same_v<T, bool>,
                "Array2D<bool> is excluded because std::vector<bool> is not "
                "contiguous T storage");

 public:
  using value_type = T;

  explicit Array2D(Shape2D shape) : shape_(shape), values_(shape.size()) {}

  Array2D(Shape2D shape, const T& initial_value)
      : shape_(shape), values_(shape.size(), initial_value) {}

  [[nodiscard]] Shape2D shape() const noexcept { return shape_; }
  [[nodiscard]] std::size_t nx() const noexcept { return shape_.nx(); }
  [[nodiscard]] std::size_t ny() const noexcept { return shape_.ny(); }
  [[nodiscard]] std::size_t size() const noexcept { return values_.size(); }
  [[nodiscard]] constexpr std::size_t stride_i() const noexcept { return 1; }
  [[nodiscard]] std::size_t stride_j() const noexcept { return shape_.nx(); }

  [[nodiscard]] T* data() noexcept { return values_.data(); }
  [[nodiscard]] const T* data() const noexcept { return values_.data(); }
  [[nodiscard]] std::span<T> values() noexcept { return values_; }
  [[nodiscard]] std::span<const T> values() const noexcept { return values_; }

  T& operator()(std::size_t i, std::size_t j) {
    return values_[linear_index(i, j)];
  }

  const T& operator()(std::size_t i, std::size_t j) const {
    return values_[linear_index(i, j)];
  }

 private:
  [[nodiscard]] std::size_t linear_index(
      std::size_t i,
      std::size_t j) const {
    if (i >= shape_.nx() || j >= shape_.ny()) {
      throw std::out_of_range("Array2D index is outside its shape");
    }
    return i + shape_.nx() * j;
  }

  Shape2D shape_;
  std::vector<T> values_;
};

template <typename T>
class Array3D {
  static_assert(std::is_object_v<T>);
  static_assert(!std::is_const_v<T> && !std::is_volatile_v<T>);
  static_assert(!std::is_same_v<T, bool>,
                "Array3D<bool> is excluded because std::vector<bool> is not "
                "contiguous T storage");

 public:
  using value_type = T;

  explicit Array3D(Shape3D shape) : shape_(shape), values_(shape.size()) {}

  Array3D(Shape3D shape, const T& initial_value)
      : shape_(shape), values_(shape.size(), initial_value) {}

  [[nodiscard]] Shape3D shape() const noexcept { return shape_; }
  [[nodiscard]] std::size_t nx() const noexcept { return shape_.nx(); }
  [[nodiscard]] std::size_t ny() const noexcept { return shape_.ny(); }
  [[nodiscard]] std::size_t nz() const noexcept { return shape_.nz(); }
  [[nodiscard]] std::size_t size() const noexcept { return values_.size(); }
  [[nodiscard]] constexpr std::size_t stride_i() const noexcept { return 1; }
  [[nodiscard]] std::size_t stride_j() const noexcept { return shape_.nx(); }
  [[nodiscard]] std::size_t stride_k() const noexcept {
    return shape_.horizontal_size();
  }

  [[nodiscard]] T* data() noexcept { return values_.data(); }
  [[nodiscard]] const T* data() const noexcept { return values_.data(); }
  [[nodiscard]] std::span<T> values() noexcept { return values_; }
  [[nodiscard]] std::span<const T> values() const noexcept { return values_; }

  T& operator()(std::size_t i, std::size_t j, std::size_t k) {
    return values_[linear_index(i, j, k)];
  }

  const T& operator()(
      std::size_t i,
      std::size_t j,
      std::size_t k) const {
    return values_[linear_index(i, j, k)];
  }

 private:
  [[nodiscard]] std::size_t linear_index(
      std::size_t i,
      std::size_t j,
      std::size_t k) const {
    if (i >= shape_.nx() || j >= shape_.ny() || k >= shape_.nz()) {
      throw std::out_of_range("Array3D index is outside its shape");
    }
    return i + shape_.nx() * (j + shape_.ny() * k);
  }

  Shape3D shape_;
  std::vector<T> values_;
};

}  // namespace cteas::atmos
