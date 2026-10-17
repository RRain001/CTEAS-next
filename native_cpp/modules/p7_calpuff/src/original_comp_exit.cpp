#include "cteas/puff/original_comp_exit.hpp"
#include <cmath>
#include <stdexcept>

namespace cteas::puff {
OriginalCompExitReason original_comp_before_step_exit(
    const std::vector<float>& qm,const std::vector<float>& qu) {
    if(qm.empty() || qm.size()!=qu.size())
        throw std::invalid_argument("COMP QALL requires aligned species arrays");
    // Original calpuff.for 10450-10457:
    // QALL=0; DO NS=1,NSPEC; QALL=QALL+QU(NS,II)+QM(NS,II).
    // Single-precision left-associative additions must be preserved.
    float qall=0.0F;
    for(std::size_t ns=0;ns<qm.size();++ns) {
        if(!std::isfinite(qm[ns])||!std::isfinite(qu[ns]))
            throw std::invalid_argument("COMP QALL nonfinite puff mass");
        qall=static_cast<float>(qall+qu[ns]);
        qall=static_cast<float>(qall+qm[ns]);
    }
    if(!std::isfinite(qall))
        throw std::invalid_argument("COMP QALL overflow");
    return qall<=0.0F?OriginalCompExitReason::ExhaustedMass:
                       OriginalCompExitReason::Active;
}
OriginalCompExitReason original_comp_after_step_exit(
    float x,float y,const OriginalCompPuffBounds& b) {
    if(!std::isfinite(x)||!std::isfinite(y)||
       !std::isfinite(b.xb)||!std::isfinite(b.xe)||
       !std::isfinite(b.yb)||!std::isfinite(b.ye)||
       b.xb>=b.xe || b.yb>=b.ye)
        throw std::invalid_argument("COMP original XY bounds/position invalid");
    // Original calpuff.for L11400-L11413, Gaussian puff center only.
    if(x<b.xb||x>b.xe||y<b.yb||y>b.ye)
        return OriginalCompExitReason::OutsideComputationalDomain;
    return OriginalCompExitReason::Active;
}
} // namespace cteas::puff
