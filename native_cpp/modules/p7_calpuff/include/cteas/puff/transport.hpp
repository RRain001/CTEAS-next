#pragma once
#include "cteas/puff/control.hpp"
#include "cteas/puff/calmet21.hpp"
#include "cteas/puff/original_grid_coords.hpp"
#include <cstddef>
#include <cstdint>
#include <vector>
namespace cteas::puff {
// P7C: only dry emission + prescribed-wind transport. NO CALPUFF puff parity,
// plume rise, dispersion, deposition or concentration claim.
struct PointRelease {
    double x_m=0, y_m=0, z_m=0;
    std::vector<double> rate_per_s; // Selected IPTU=8, Bq/s; still a P7C-only transport prototype.
};
struct PuffPacket {
    std::uint64_t id=0;
    double x_m=0, y_m=0, z_m=0;
    std::vector<double> mass;
    bool active=true;
};
struct WindField {
    int nx=0,ny=0,nz=0;
    double origin_x_m=0,origin_y_m=0,spacing_m=0;
    std::vector<double> level_m;
    // Native CALMET fields [z][j][i], i fastest.
    std::vector<float> u,v,w;
    void validate() const;
    bool contains(double x,double y,double z) const;
    std::vector<double> velocity(double x,double y,double z) const;
};
struct MassBalance {
    std::vector<double> released, inventory, outflow;
    std::size_t active=0,total=0;
};
class PuffTransport {
public:
    explicit PuffTransport(std::size_t species);
    void emit(const PointRelease&,double dt_seconds);
    void advect(const WindField&,double dt_seconds);
    [[nodiscard]] MassBalance balance() const;
    [[nodiscard]] const std::vector<PuffPacket>& packets() const {return packets_;}
private:
    std::size_t species_;
    std::uint64_t next_id_=1;
    std::vector<double> released_,outflow_;
    std::vector<PuffPacket> packets_;
};
[[nodiscard]] PointRelease point_source_from_control(const ControlFile&);
// Original-CALMET-frame-aware source coordinates for selected Hefei 2022.
// The old one-argument overload is retained for the standalone absolute-UTM
// P7C prototype, and must NOT be used to claim original QA coordinate parity.
[[nodiscard]] PointRelease point_source_from_original_met_grid(
    const ControlFile&, const OriginalMetGridFrame&);
[[nodiscard]] std::vector<double> level_centers_from_zface(const std::vector<double>&);
// Deterministic P7C dry replay of ORIGINAL CALMET meteorology.
// One hour of U/V/W arrays is retained at once; original meteorology is
// decoded twice (first to validate header, second to replay all hours).
// No claim of original CALPUFF release schedule or concentration parity.
struct ReplaySummary {
    Calmet21Summary met;
    MassBalance mass;
    std::size_t wind_hours=0,substeps=0;
};
[[nodiscard]] ReplaySummary replay_calmet_winds(
    const std::string& met_file, const SelectedDryInputs& inputs,
    const PointRelease& source, bool require_historical_2023);
} // namespace cteas::puff
