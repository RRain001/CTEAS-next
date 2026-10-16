#pragma once

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <span>
#include <stdexcept>

#include "cteas_atmos/core/array.hpp"

namespace cteas::atmos {

enum class Validity : std::uint8_t {
  missing = 0,
  valid = 1,
};

static_assert(sizeof(Validity) == 1);

[[nodiscard]] inline bool is_known_validity(Validity state) noexcept {
  switch (state) {
    case Validity::missing:
    case Validity::valid:
      return true;
  }
  return false;
}

[[nodiscard]] inline bool validity_is_valid(Validity state) {
  switch (state) {
    case Validity::missing:
      return false;
    case Validity::valid:
      return true;
  }
  throw std::invalid_argument("unknown Validity value");
}

[[nodiscard]] inline bool validity_is_missing(Validity state) {
  return !validity_is_valid(state);
}

class ValidityMask2D {
 public:
  explicit ValidityMask2D(Shape2D shape)
      : states_(shape, Validity::missing) {}

  ValidityMask2D(Shape2D shape, Validity initial_state)
      : states_(shape, checked_state(initial_state)) {}

  [[nodiscard]] Shape2D shape() const noexcept { return states_.shape(); }
  [[nodiscard]] std::size_t nx() const noexcept { return states_.nx(); }
  [[nodiscard]] std::size_t ny() const noexcept { return states_.ny(); }
  [[nodiscard]] std::size_t size() const noexcept { return states_.size(); }

  [[nodiscard]] Validity state(std::size_t i, std::size_t j) const {
    return states_(i, j);
  }
  [[nodiscard]] bool is_valid(std::size_t i, std::size_t j) const {
    return validity_is_valid(state(i, j));
  }
  [[nodiscard]] bool is_missing(std::size_t i, std::size_t j) const {
    return validity_is_missing(state(i, j));
  }

  void set(std::size_t i, std::size_t j, Validity state_value) {
    states_(i, j) = checked_state(state_value);
  }
  void set_valid(std::size_t i, std::size_t j) {
    states_(i, j) = Validity::valid;
  }
  void set_missing(std::size_t i, std::size_t j) {
    states_(i, j) = Validity::missing;
  }
  void fill(Validity state_value) {
    const Validity checked = checked_state(state_value);
    std::fill(states_.values().begin(), states_.values().end(), checked);
  }
  void fill_valid() { fill(Validity::valid); }
  void fill_missing() { fill(Validity::missing); }

  [[nodiscard]] const Validity* data() const noexcept {
    return states_.data();
  }
  [[nodiscard]] std::span<const Validity> raw_states() const noexcept {
    return states_.values();
  }

 private:
  [[nodiscard]] static Validity checked_state(Validity state_value) {
    if (!is_known_validity(state_value)) {
      throw std::invalid_argument("unknown Validity value");
    }
    return state_value;
  }

  Array2D<Validity> states_;
};

class ValidityMask3D {
 public:
  explicit ValidityMask3D(Shape3D shape)
      : states_(shape, Validity::missing) {}

  ValidityMask3D(Shape3D shape, Validity initial_state)
      : states_(shape, checked_state(initial_state)) {}

  [[nodiscard]] Shape3D shape() const noexcept { return states_.shape(); }
  [[nodiscard]] std::size_t nx() const noexcept { return states_.nx(); }
  [[nodiscard]] std::size_t ny() const noexcept { return states_.ny(); }
  [[nodiscard]] std::size_t nz() const noexcept { return states_.nz(); }
  [[nodiscard]] std::size_t size() const noexcept { return states_.size(); }

  [[nodiscard]] Validity state(
      std::size_t i,
      std::size_t j,
      std::size_t k) const {
    return states_(i, j, k);
  }
  [[nodiscard]] bool is_valid(
      std::size_t i,
      std::size_t j,
      std::size_t k) const {
    return validity_is_valid(state(i, j, k));
  }
  [[nodiscard]] bool is_missing(
      std::size_t i,
      std::size_t j,
      std::size_t k) const {
    return validity_is_missing(state(i, j, k));
  }

  void set(
      std::size_t i,
      std::size_t j,
      std::size_t k,
      Validity state_value) {
    states_(i, j, k) = checked_state(state_value);
  }
  void set_valid(std::size_t i, std::size_t j, std::size_t k) {
    states_(i, j, k) = Validity::valid;
  }
  void set_missing(std::size_t i, std::size_t j, std::size_t k) {
    states_(i, j, k) = Validity::missing;
  }
  void fill(Validity state_value) {
    const Validity checked = checked_state(state_value);
    std::fill(states_.values().begin(), states_.values().end(), checked);
  }
  void fill_valid() { fill(Validity::valid); }
  void fill_missing() { fill(Validity::missing); }

  [[nodiscard]] const Validity* data() const noexcept {
    return states_.data();
  }
  [[nodiscard]] std::span<const Validity> raw_states() const noexcept {
    return states_.values();
  }

 private:
  [[nodiscard]] static Validity checked_state(Validity state_value) {
    if (!is_known_validity(state_value)) {
      throw std::invalid_argument("unknown Validity value");
    }
    return state_value;
  }

  Array3D<Validity> states_;
};

}  // namespace cteas::atmos
