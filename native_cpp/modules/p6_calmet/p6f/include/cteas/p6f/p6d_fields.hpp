#pragma once
// ---------------------------------------------------------------------------
// P6F input adapter: consume the P6D real-case wind-field array product.
//
// The P6D producer (`cteas_p6_realcase_wind_field`, module
// native_cpp/modules/p6_calmet) writes, per hour, one raw little-endian float32
// plane per field and a `metadata.json`:
//
//   <dir>/metadata.json
//   <dir>/produced_hours.txt                    (whitespace separated labels)
//   <dir>/<variant>_u_<label>.f32               nx*ny*nz, idx = i + nx*(j + ny*k)
//   <dir>/<variant>_v_<label>.f32
//   <dir>/w_face_<label>.f32                    nx*ny*(nz+1), face k=1 is ground
//   <dir>/terset_hmax.f32, terset_hmin.f32, terset_disthmax.f32,
//        terset_disthmin.f32                    (case-invariant planes, unused here)
//   <dir>/temp2d_<label>.f32, qh_<label>.f32    (provenance extras, unused here)
//   <dir>/windbc_ub|vb_<label>.f32              WINDBC lateral boundaries, not a
//                                               gridded field: rejected here
//
// `variant` is the producer's own prefix. The P6D product has renamed one of
// them over time: the pre-tail INTER2 field was `blend_*` and is now `inter2_*`,
// while `blend_*` holds the closed DIAGNO field (INTER2 -> SMOOTH -> DIVCEL).
// Both names are accepted and the choice is the caller's, because the metadata
// carries the verdict of each. `windbc_*` is not a gridded CALMET field and is
// refused.
//
// `metadata.json` carries grid{nx,ny,nz,grid_spacing_m,layout,dtype},
// levels{zface_m,...}, units{...}, missing_sentinel, hour_label and
// hourly_labels. This adapter reads the dimensions, the cell face heights, the
// sentinel and the label semantics from that file instead of hard-coding them,
// so a later corrected W product can replace `w_face` without a schema change.
//
// The adapter does NOT invent values: the static records, the run controls and
// the projection block are case input and are taken from an existing legal
// CALMET.DAT 2.1 file (`statics_from`), and the declared run window and IRLG are
// derived from the interval set actually written. With IRTYPE=1 the 2-D
// meteorological fields must additionally come from another legal file
// (`met_fields_from`), because the P6D contract contains only U, V and W.
//
// CALMET.DAT writes W at the top face of each layer: WFACE(k) = w_face(k+1) for
// k=1..NZ, i.e. the ground face k=1 is not written.
// ---------------------------------------------------------------------------
#include <cstddef>
#include <string>
#include <vector>

#include "cteas/p6f/calmet_dat21_writer.hpp"

namespace cteas::p6f {

struct P6dFieldsMetadata {
    int nx = 0, ny = 0, nz = 0;
    float grid_spacing_m = 0.f;
    std::vector<float> zface_m;      // NZ+1 cell faces in metres
    float missing_sentinel = missing_real;
    bool label_is_interval_end = true;  // metadata.hour_label
    std::string layout;                 // raw string as read from the file
    std::string dtype;                  // raw string as read from the file
    // `hourly_labels` is an array of labels in the published schema and a bare
    // count in the real product; both spellings are read.
    std::vector<std::string> hourly_labels;
    int hourly_label_count = 0;
    std::string product;
    std::string status;
    bool partial = false;
    // provenance P6D publishes alongside the arrays: the blend verification
    // verdict and the FRADJ stage status, reported (and acted on) rather than
    // silently assumed.
    std::string blend_verification;
    std::string fradj_status;
};

// Strict, fail-closed reader of <dir>/metadata.json.
P6dFieldsMetadata read_p6d_fields_metadata(const std::string& metadata_path);
// The labels listed by <dir>/produced_hours.txt (sorted chronologically).
std::vector<std::string> read_p6d_produced_hours(const std::string& path);

struct P6dWindHour {
    std::string label;
    std::vector<float> u_mps;        // nx*ny*nz, i-fastest
    std::vector<float> v_mps;        // nx*ny*nz, i-fastest
    std::vector<float> w_face_mps;   // nx*ny*(nz+1), i-fastest
};

// Raw little-endian float32 plane; size must match `count` exactly.
std::vector<float> read_p6d_plane(const std::string& path, std::size_t count);

P6dWindHour read_p6d_wind_hour(const std::string& directory,
                               const std::string& variant,
                               const std::string& w_field,
                               const std::string& label,
                               const P6dFieldsMetadata& metadata);

// Compose the writable dataset: declaration/statics/controls from
// `statics_from`, hourly U/V/W from the P6D planes, and - for IRTYPE=1 - the
// 2-D meteorological fields taken verbatim from `met_fields_from`.
// `allow_unverified` is the explicit opt-in required to write a variant that the
// P6D metadata marks NOT_SOURCE_VERIFIED (currently `blend`, and the fields built
// on it). Without it such a selection fails closed.
Calmet21File build_calmet_from_p6d(const std::string& directory,
                                   const std::string& variant,
                                   const std::string& w_field,
                                   const std::vector<std::string>& labels,
                                   const Calmet21File& statics_from,
                                   const Calmet21File* met_fields_from,
                                   int irtype, bool allow_unverified);

}  // namespace cteas::p6f
