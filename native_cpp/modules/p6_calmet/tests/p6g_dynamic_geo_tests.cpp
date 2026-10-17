#include "cteas/p6/read_geo_dynamic.hpp"
#include "cteas/p6/read_geo.hpp"
#include <cstdio>
#include <cmath>
#include <exception>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <tuple>
#include <vector>

using cteas::calmet::p6g::GeoGrid;
using cteas::calmet::p6g::GeoGridSpec;
using cteas::calmet::p6g::read_geo_dynamic;

static void expect(bool valid,const char* message) {
    if(!valid)throw std::runtime_error(message);
}

static void fixture(const std::string& path,int nx,int ny,double dx=0.1,
                    int zone=50,char hemi='N',bool extra=false) {
    std::ofstream out(path);
    if(!out)throw std::runtime_error("cannot write synthetic GEO.DAT");
    out<<"GEO.DAT         2.1             Header structure with coordinate parameters\n";
    out<<"   2\nG6 first comment\nG6 second comment\n";
    out<<"UTM\n";
    out<<"  "<<zone<<hemi<<"\n";
    out<<"WGS-84  02-21-2003\n";
    out<<" "<<nx<<" "<<ny<<" 510.885 3531.269 "<<dx<<" "<<dx<<"\n";
    out<<"KM  M\n";
    out<<" 1 - land use category table\n";
    out<<" 14 50 55 - NLU IWAT1 IWAT2\n";
    out<<"10 -20 20 30 40 51 54 55 60 61 62 70 80 90 - categories\n";
    for(int j=ny-1;j>=0;--j) {
        for(int i=0;i<nx;++i) {
            out<<((i+j)%2==0?20:51)<<",";
            if(i%11==10||i==nx-1)out<<"\n";
        }
    }
    out<<" 1.0000 - HTFAC\n";
    for(int j=ny-1;j>=0;--j)for(int i=0;i<nx;++i)
        out<<100+i+2*j<<(i==nx-1?"\n":",");
    for(int k=0;k<6;++k) {
        out<<"2 - gridded\n";
        for(int j=ny-1;j>=0;--j)for(int i=0;i<nx;++i)
            out<<(k==0?0.1:0.2+0.02*k)<<(i==nx-1?"\n":",");
    }
    if(extra)out<<"extraneous GEO.DAT data\n";
}

int main() {
    const std::string path="g6_geo_dynamic_fixture.txt";
    try {
        for(const auto& [nx,ny,spacing]:std::vector<std::tuple<int,int,double>>{
                {50,50,0.1},{13,7,0.5},{120,64,2.0},{1,1,1.0}}) {
            fixture(path,nx,ny,spacing);
            const GeoGridSpec spec{nx,ny,50,'N',510.885,3531.269,spacing};
            auto geo=read_geo_dynamic(path,spec);
            const auto count=static_cast<std::size_t>(nx)*static_cast<std::size_t>(ny);
            expect(geo.nx==nx&&geo.ny==ny,"dynamic grid shape");
            for(const auto* array:{&geo.landuse})expect(array->size()==count,"landuse size");
            for(const auto* array:{&geo.terrain_m,&geo.z0_m,&geo.albedo,
                                   &geo.bowen,&geo.hcg,&geo.qf,&geo.lai})
                expect(array->size()==count,"field size");
            expect(geo.terrain_m.front()==100.0f,"southwest terrain orientation");
            expect(geo.terrain_m.back()==static_cast<float>(100+nx-1+2*(ny-1)),
                   "northeast terrain orientation");
            expect(geo.landuse[0]==20&&geo.z0_m[0]>0,"category + z0");
            if(nx==50&&ny==50&&spacing==0.1) {
                const auto frozen=cteas::calmet::p6::read_geo_50(path,510.885,3531.269);
                expect(frozen.landuse==geo.landuse,"50x50 landuse exact parity");
                expect(frozen.terrain_m==geo.terrain_m,"50x50 terrain exact parity");
                expect(frozen.z0_m==geo.z0_m,"50x50 z0 exact parity");
                expect(frozen.albedo==geo.albedo&&frozen.bowen==geo.bowen&&
                       frozen.hcg==geo.hcg&&frozen.qf==geo.qf&&frozen.lai==geo.lai,
                       "50x50 seven field exact parity");
            }
        }
        fixture(path,13,7,0.5);
        const GeoGridSpec good{13,7,50,'N',510.885,3531.269,0.5};
        auto must_reject=[&](const GeoGridSpec& spec,const char* what) {
            bool rejected=false;
            try{(void)read_geo_dynamic(path,spec);}
            catch(const std::runtime_error&){rejected=true;}
            expect(rejected,what);
        };
        must_reject({12,7,50,'N',510.885,3531.269,0.5},"wrong NX");
        must_reject({13,8,50,'N',510.885,3531.269,0.5},"wrong NY");
        must_reject({13,7,51,'N',510.885,3531.269,0.5},"wrong zone");
        must_reject({13,7,50,'S',510.885,3531.269,0.5},"wrong hemisphere");
        must_reject({13,7,50,'N',510.885,3531.269,0.2},"wrong spacing");
        must_reject({13,7,50,'N',509.0,3531.269,0.5},"wrong origin");
        must_reject({0,7,50,'N',510.885,3531.269,0.5},"zero grid");
        must_reject({500000,500000,50,'N',510.885,3531.269,0.5},"oversize allocation");
        fixture(path,13,7,0.5,50,'N',true);
        must_reject(good,"trailing GEO data");
        std::remove(path.c_str());
        std::cout<<"PASS P6G_G6_DYNAMIC_GEO_MULTIRES_MULTI_SHAPE_FROZEN_EQUALITY\n";
        return 0;
    }catch(const std::exception& e){
        std::remove(path.c_str());
        std::cerr<<"P6G_G6_DYNAMIC_GEO_FAIL "<<e.what()<<'\n';
        return 1;
    }
}
