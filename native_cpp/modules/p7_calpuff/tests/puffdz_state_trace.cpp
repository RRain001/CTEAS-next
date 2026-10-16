#include "cteas/puff/advection.hpp"

#include <array>
#include <bit>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <unordered_map>

namespace {
struct Record {std::array<std::int32_t,24> i;std::array<float,64> f;};
static_assert(sizeof(Record)==352U);
static_assert(std::endian::native==std::endian::little);
void require(bool ok,const char* why) {if(!ok)throw std::runtime_error(why);}
}
int main(int argc,char** argv) {
    try {
        using namespace cteas::puff;
        require(argc==3 || argc==4,
                "usage: cteas_p7_puffdz_state_trace ORIGINAL_DGM EXPECTED_HOURS [ORIGINAL_ZI_8BYTE_STREAM]");
        const int nh=std::stoi(argv[2]);
        require(nh==1 || nh==6 || nh==143,"only frozen 1/6/143h allowed");
        std::ifstream in(argv[1],std::ios::binary);
        require(bool(in),"missing original DGM binary");
        const bool original_zi_available=argc==4;
        std::ifstream zi;
        if(original_zi_available) {
            zi.open(argv[3],std::ios::binary);
            require(bool(zi),"missing original read-only ZIOLD/ZIMAX oracle");
        }
        std::unordered_map<int,float> previous_sigz;
        int previous_hour=-1;
        std::size_t records=0,compared=0,skipped=0,mismatched=0,episodes=0;
        Record r{};
        while(in.read(reinterpret_cast<char*>(&r),sizeof(r))) {
            ++records;
            require(r.i[0]==1 && r.i[1]/100000==2022 && r.i[2]==0,
                    "wrong original DGM stamp/type");
            const int hour=(r.i[1]/100%1000-1)*24+r.i[1]%100;
            require(hour>=0 && hour<nh && (previous_hour==-1 ||
                    hour==previous_hour || hour==previous_hour+1),
                    "DGM hours reordered or outside requested time span");
            previous_hour=hour;
            const int id=r.i[3];
            require(id>0 && r.i[19]==1 && r.i[20]==0,
                    "selected original DGM contains a non-Gaussian slug");
            const bool new_puff=r.f[19]==0.0F && r.f[20]==0.0F;
            auto it=previous_sigz.find(id);
            if(new_puff) {
                // Original frozen 2022 POINTS1 gives a new gas puff SIGZ=1m;
                // the native initial state must not be re-seeded from DGM.
                require(it==previous_sigz.end(),"original reused puff identifier");
                ++episodes;
            } else {
                require(it!=previous_sigz.end(),"missing previous puff state");
            }
            const float sigma=new_puff?1.0F:it->second;
            std::array<float,2> original_zi{};
            if(original_zi_available) {
                zi.read(reinterpret_cast<char*>(original_zi.data()),
                        sizeof(original_zi));
                require(zi.gcount()==static_cast<std::streamsize>(sizeof(original_zi)),
                        "original ZI state missing a puff-step record");
                require(std::isfinite(original_zi[0]) &&
                        std::isfinite(original_zi[1]) &&
                        original_zi[0]>=0.0F && original_zi[1]>=0.0F,
                        "original ZI state contains an invalid height");
            }
            const bool determinate = (r.i[4]%2==1) &&
                 (r.i[8]>4 || r.i[4]==3 || r.i[4]==13 || r.f[3]>r.f[2]);
            if(determinate || original_zi_available) {
                PuffExtentInputs p;
                p.puff_code=r.i[4];
                p.puff=true;
                p.stability_class=r.i[8];
                p.puff_height_m=r.f[2];
                p.mixing_height_m=r.f[3];
                p.sigma_z_begin_m=sigma;
                // For the previously indeterminate original branch these
                // two values are read from a separately instrumented,
                // ORIGINAL Fortran run. A missing stream never defaults to
                // any guessed value. In all other branches they are ignored.
                p.previous_mixing_height_m=original_zi[0];
                p.maximum_mixing_height_m=original_zi[1];
                auto v=puff_extent(p);
                const float top=static_cast<float>(v.z_top_m);
                const float bot=static_cast<float>(v.z_bottom_m);
                ++compared;
                if(top!=r.f[7] || bot!=r.f[8]) {
                    ++mismatched;
                    if(mismatched<=8)
                        std::cerr<<"P7_PUFFDZ_FIRST_DIFFERENCE ROW="<<records
                            <<" HOUR="<<hour<<" PUFF="<<id
                            <<" PREV_SIGZ="<<sigma
                            <<" TOP_NATIVE="<<top<<" TOP_ORIGINAL="<<r.f[7]
                            <<" BOT_NATIVE="<<bot<<" BOT_ORIGINAL="<<r.f[8]<<"\n";
                }
            } else {
                ++skipped;
            }
            previous_sigz[id]=r.f[43]; // previous native puff state is not yet
                                        // propagated through full SIGTZ/SETPUF
        }
        require(in.eof() && in.gcount()==0,"DGM record is incomplete");
        if(original_zi_available) {
            require(zi.peek()==std::char_traits<char>::eof(),
                    "original ZI stream has surplus records");
            require(zi.eof(),"original ZI stream ended unexpectedly");
        }
        require(previous_hour==nh-1,"frozen source didn't reach final hour");
        require(records==(nh==1?1275U:nh==6?11458U:254687U),
                "DGM row count not original pinned 1/6/143-hour scope");
        require(compared>0 && compared+skipped==records,
                "PUFFDZ coverage bookkeeping incomplete");
        std::cout<<"P7_NATIVE_PUFFDZ_DETERMINATE CHECKED="<<compared
                 <<" MISMATCHED="<<mismatched<<" SKIPPED_UNDETERMINED="<<skipped
                 <<" ORIGINAL_RECORDS="<<records
                 <<" PUFF_EPISODES="<<episodes
                 <<" ORIGINAL_SIGZ_STATE_FED=YES"
                 <<" ORIGINAL_ZI_STATE_FED="<<(original_zi_available?"YES":"NO")<<"\n";
        if(mismatched!=0) return 2;
        if(original_zi_available) {
            require(skipped==0 && compared==records,
                    "original ZI inputs supplied but any puff was skipped");
            std::cout<<"P7_NATIVE_PUFFDZ_FULL_ZI_PARITY=PASS HOURS="<<nh
                     <<" EXACT_RECORDS="<<compared
                     <<" MISMATCHED="<<mismatched
                     <<" UNTESTED=0"
                     <<" ORIGINAL_SIGZ_ZI_ORACLE_FED=YES\n";
        }
        std::cout<<"P7_NATIVE_PUFFDZ=PASS HOURS="<<nh
                 <<" DETERMINATE="<<compared
                 <<" SKIPPED_UNDETERMINED="<<skipped
                 <<" HISTORICAL_ZI_ORIGINAL_MISSING="
                 <<(original_zi_available?"NO":"YES")<<"\n";
        return 0;
    }catch(const std::exception& e) {
        std::cerr<<"P7_NATIVE_PUFFDZ=FAIL "<<e.what()<<"\n";
        return 1;
    }
}
