#pragma once

#include "cteas/puff/calmet21.hpp"
#include "cteas/puff/original_puffct2.hpp"
#include "cteas/puff/terrain_constraints.hpp"
#include <memory>

namespace cteas::puff {

// Physical original TRELIEF -> VWIDTH -> GETELEV/GETCELL terrain grid
// constructed only from native CALMET.DAT static OUTHD ELEV (no DGM).
// The existing P7S/P7T source ports own the formulas; this bridge owns
// lifetime, indexing and explicit provenance for MCTADJ=2 callers.
class OriginalNativeTerrain {
public:
    [[nodiscard]] static OriginalNativeTerrain from_calmet(
        const Calmet21Static& statics,int nx,int ny,float met_spacing_m);
    // CTADJ2 + WALLTRAP callback object. Lambda state owns the full
    // terrain cache even when this adapter's temporary object dies.
    [[nodiscard]] TerrainLookup constraint_lookup() const;
    // Original PUFRECS L5333-5359; one receptor index in a gridded
    // sampling frame, with actual post-PUFFCT2 puff position.
    [[nodiscard]] OriginalMctadj2ReceptorTerrain receptor(
        std::size_t receptor_flat_0based,
        int ibsamp,int jbsamp,int sampling_nx,int sampling_ny,
        const OriginalPuffct2Result& puff_position,
        float native_bvf_s,float native_uavg_ms,
        float receptor_pole_m=0.0F) const;
private:
    struct Data;
    explicit OriginalNativeTerrain(std::shared_ptr<const Data> data);
    std::shared_ptr<const Data> data_;
};

} // namespace cteas::puff
