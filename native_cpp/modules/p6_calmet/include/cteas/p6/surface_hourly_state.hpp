#pragma once
// Original CALMET 6.5.0 RDSN selected explicit start/end time state:
// calmet.for L23526-23534 (reuse) and L23598-23636 (record coverage).
// Scoped: SURF.DAT v2.1, IFORMS=2, NSSTA=1, UTC; no MISSFC inference.
#include "cteas/p6/read_surface.hpp"
#include <chrono>
#include <cstddef>
#include <stdexcept>

namespace cteas::calmet::p6 {
struct RdsnHourlyState {
    const SurfaceInterval* record=nullptr;
    std::size_t source_row=0;
    std::size_t reads=0;
    bool reused=false;
};
class RdsnBufferedTimeline {
public:
    explicit RdsnBufferedTimeline(const Surface2022& input,int timestep_seconds=3600)
        : input_(input),timestep_seconds_(timestep_seconds) {
        if(input_.hourly.empty() || timestep_seconds_<=0 ||
           timestep_seconds_>3600 || 3600%timestep_seconds_!=0)
            throw std::invalid_argument("RDSN invalid CALMET timestep or empty input");
    }
    RdsnHourlyState select(std::chrono::sys_seconds start,
                           std::chrono::sys_seconds end) {
        using namespace std::chrono;
        if(end-start!=seconds{timestep_seconds_})
            throw std::invalid_argument("RDSN timestep mismatch");
        if(visited_ && start!=previous_end_)
            throw std::invalid_argument("RDSN time discontinuity");
        if(!visited_ && start!=input_.hourly.front().start)
            throw std::invalid_argument("RDSN unsupported initial record offset");
        const auto covered=[](const SurfaceInterval& r,sys_seconds t) {
            return r.start<=t && t<r.end;
        };
        bool reused=visited_ && covered(input_.hourly.at(index_),start);
        if(!reused) {
            // Fortran RDSN may advance over records ending <= current start.
            // It fails if the next record starts after the current start.
            while(index_<input_.hourly.size() && input_.hourly[index_].end<=start)
                ++index_;
            if(index_>=input_.hourly.size() || !covered(input_.hourly[index_],start))
                throw std::invalid_argument("RDSN surface record gap");
            ++reads_;
        }
        const auto& row=input_.hourly.at(index_);
        if(row.end-row.start>hours{1})
            throw std::invalid_argument("RDSN record duration >1h");
        if(row.end-row.start<seconds{timestep_seconds_})
            throw std::invalid_argument("COMP surface frequency exceeds timestep");
        if(end>row.end)
            throw std::invalid_argument("RDSN current timestep not fully covered");
        RdsnHourlyState state;
        state.record=&row;
        state.source_row=index_;
        state.reads=reads_;
        state.reused=reused;
        visited_=true;
        previous_end_=end;
        return state;
    }
private:
    const Surface2022& input_;
    int timestep_seconds_;
    std::size_t index_=0,reads_=0;
    bool visited_=false;
    std::chrono::sys_seconds previous_end_{};
};
} // namespace cteas::calmet::p6
