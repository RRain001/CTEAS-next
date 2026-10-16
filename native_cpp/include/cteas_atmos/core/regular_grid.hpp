#pragma once

#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include "cteas_atmos/core/shape.hpp"

namespace cteas::atmos {

class RegularHorizontalGrid {
 public:
  RegularHorizontalGrid(
      Shape2D cell_shape,
      double x0_m,
      double y0_m,
      double dx_m,
      double dy_m)
      : cell_shape_(cell_shape),
        x0_m_(checked_finite(x0_m, "x0")),
        y0_m_(checked_finite(y0_m, "y0")),
        dx_m_(checked_positive_finite(dx_m, "dx")),
        dy_m_(checked_positive_finite(dy_m, "dy")) {
    (void)detail::checked_add_one(cell_shape_.nx(), "horizontal x-face");
    (void)detail::checked_add_one(cell_shape_.ny(), "horizontal y-face");
    (void)coordinate(x0_m_, dx_m_, cell_shape_.nx(), "east x-face");
    (void)coordinate(y0_m_, dy_m_, cell_shape_.ny(), "north y-face");
  }

  [[nodiscard]] Shape2D cell_shape() const noexcept { return cell_shape_; }
  [[nodiscard]] std::size_t nx() const noexcept { return cell_shape_.nx(); }
  [[nodiscard]] std::size_t ny() const noexcept { return cell_shape_.ny(); }
  [[nodiscard]] double x0_m() const noexcept { return x0_m_; }
  [[nodiscard]] double y0_m() const noexcept { return y0_m_; }
  [[nodiscard]] double dx_m() const noexcept { return dx_m_; }
  [[nodiscard]] double dy_m() const noexcept { return dy_m_; }

  [[nodiscard]] double x_cell_center(std::size_t i) const {
    check_cell_index(i, cell_shape_.nx(), "x cell-center");
    return coordinate(x0_m_, dx_m_, static_cast<double>(i) + 0.5,
                      "x cell-center");
  }

  [[nodiscard]] double y_cell_center(std::size_t j) const {
    check_cell_index(j, cell_shape_.ny(), "y cell-center");
    return coordinate(y0_m_, dy_m_, static_cast<double>(j) + 0.5,
                      "y cell-center");
  }

  [[nodiscard]] double x_face(std::size_t i_face) const {
    check_face_index(i_face, cell_shape_.nx(), "x-face");
    return coordinate(x0_m_, dx_m_, i_face, "x-face");
  }

  [[nodiscard]] double y_face(std::size_t j_face) const {
    check_face_index(j_face, cell_shape_.ny(), "y-face");
    return coordinate(y0_m_, dy_m_, j_face, "y-face");
  }

 private:
  [[nodiscard]] static double checked_finite(double value, const char* name) {
    if (!std::isfinite(value)) {
      throw std::invalid_argument(std::string{name} + " must be finite");
    }
    return value;
  }

  [[nodiscard]] static double checked_positive_finite(
      double value,
      const char* name) {
    if (!std::isfinite(value) || value <= 0.0) {
      throw std::invalid_argument(std::string{name} +
                                  " must be finite and greater than zero");
    }
    return value;
  }

  static void check_cell_index(
      std::size_t index,
      std::size_t extent,
      const char* name) {
    if (index >= extent) {
      throw std::out_of_range(std::string{name} + " index is out of range");
    }
  }

  static void check_face_index(
      std::size_t index,
      std::size_t cell_extent,
      const char* name) {
    if (index > cell_extent) {
      throw std::out_of_range(std::string{name} + " index is out of range");
    }
  }

  [[nodiscard]] static double coordinate(
      double origin,
      double spacing,
      std::size_t index,
      const char* name) {
    return coordinate(
        origin, spacing, static_cast<double>(index), name);
  }

  [[nodiscard]] static double coordinate(
      double origin,
      double spacing,
      double offset,
      const char* name) {
    const double value = origin + offset * spacing;
    if (!std::isfinite(value)) {
      throw std::overflow_error(std::string{name} +
                                " coordinate is not finite");
    }
    return value;
  }

  Shape2D cell_shape_;
  double x0_m_;
  double y0_m_;
  double dx_m_;
  double dy_m_;
};

class VerticalGrid {
 public:
  explicit VerticalGrid(std::vector<double> z_interface_agl_m)
      : z_interface_agl_m_(std::move(z_interface_agl_m)) {
    if (z_interface_agl_m_.size() < 2) {
      throw std::invalid_argument(
          "VerticalGrid requires at least two interfaces");
    }
    if (!std::isfinite(z_interface_agl_m_.front()) ||
        z_interface_agl_m_.front() != 0.0) {
      throw std::invalid_argument(
          "VerticalGrid first AGL interface must be exactly zero");
    }

    z_center_agl_m_.reserve(z_interface_agl_m_.size() - 1);
    for (std::size_t k = 0; k + 1 < z_interface_agl_m_.size(); ++k) {
      const double lower = z_interface_agl_m_[k];
      const double upper = z_interface_agl_m_[k + 1];
      if (!std::isfinite(lower) || !std::isfinite(upper)) {
        throw std::invalid_argument(
            "VerticalGrid interfaces must all be finite");
      }
      if (!(upper > lower)) {
        throw std::invalid_argument(
            "VerticalGrid interfaces must be strictly increasing");
      }
      const double center = lower + (upper - lower) * 0.5;
      if (!std::isfinite(center)) {
        throw std::overflow_error(
            "VerticalGrid layer center is not finite");
      }
      z_center_agl_m_.push_back(center);
    }
  }

  [[nodiscard]] std::size_t nz() const noexcept {
    return z_center_agl_m_.size();
  }
  [[nodiscard]] std::size_t interface_count() const noexcept {
    return z_interface_agl_m_.size();
  }

  [[nodiscard]] double z_interface_agl_m(std::size_t k_interface) const {
    if (k_interface >= z_interface_agl_m_.size()) {
      throw std::out_of_range(
          "VerticalGrid interface index is out of range");
    }
    return z_interface_agl_m_[k_interface];
  }

  [[nodiscard]] double z_center_agl_m(std::size_t k) const {
    if (k >= z_center_agl_m_.size()) {
      throw std::out_of_range(
          "VerticalGrid layer-center index is out of range");
    }
    return z_center_agl_m_[k];
  }

  [[nodiscard]] const std::vector<double>& interfaces_agl_m() const noexcept {
    return z_interface_agl_m_;
  }
  [[nodiscard]] const std::vector<double>& centers_agl_m() const noexcept {
    return z_center_agl_m_;
  }

 private:
  std::vector<double> z_interface_agl_m_;
  std::vector<double> z_center_agl_m_;
};

class RegularGrid3D {
 public:
  RegularGrid3D(
      RegularHorizontalGrid horizontal,
      VerticalGrid vertical)
      : horizontal_(std::move(horizontal)),
        vertical_(std::move(vertical)),
        cell_shape_(
            horizontal_.nx(), horizontal_.ny(), vertical_.nz()) {}

  [[nodiscard]] const RegularHorizontalGrid& horizontal() const noexcept {
    return horizontal_;
  }
  [[nodiscard]] const VerticalGrid& vertical() const noexcept {
    return vertical_;
  }
  [[nodiscard]] Shape3D cell_shape() const noexcept { return cell_shape_; }
  [[nodiscard]] std::size_t nx() const noexcept { return cell_shape_.nx(); }
  [[nodiscard]] std::size_t ny() const noexcept { return cell_shape_.ny(); }
  [[nodiscard]] std::size_t nz() const noexcept { return cell_shape_.nz(); }
  [[nodiscard]] double x_cell_center(std::size_t i) const {
    return horizontal_.x_cell_center(i);
  }
  [[nodiscard]] double y_cell_center(std::size_t j) const {
    return horizontal_.y_cell_center(j);
  }
  [[nodiscard]] double x_face(std::size_t i_face) const {
    return horizontal_.x_face(i_face);
  }
  [[nodiscard]] double y_face(std::size_t j_face) const {
    return horizontal_.y_face(j_face);
  }
  [[nodiscard]] double z_center_agl_m(std::size_t k) const {
    return vertical_.z_center_agl_m(k);
  }
  [[nodiscard]] double z_interface_agl_m(std::size_t k_interface) const {
    return vertical_.z_interface_agl_m(k_interface);
  }

 private:
  RegularHorizontalGrid horizontal_;
  VerticalGrid vertical_;
  Shape3D cell_shape_;
};

}  // namespace cteas::atmos
