#include "cteas/p6/read_geo.hpp"
#include <exception>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

static void check(bool good,const char* reason) {
    if(!good)throw std::runtime_error(reason);
}
static void fixture(const std::string& path,const std::string& crs="UTM     ",
                    const std::string& option=" 2  - gridded",
                    int nx=50,bool extra=false) {
    std::ofstream out(path);
    out<<"GEO.DAT         2.1             Header structure with coordinate parameters\n";
    out<<"   2\n";
    out<<"P6C synthetic first comment\nP6C synthetic second comment\n";
    out<<crs<<"\n";
    out<<"  50N   \n";
    out<<"WGS-84  02-21-2003  \n";
    out<<"      "<<nx<<"      50     510.885    3531.269       0.100       0.100\n";
    out<<"KM  M   \n";
    out<<" 1 - land use custom categories\n";
    out<<"  14  50  55 - NLU / IWAT\n";
    out<<"10 -20 20 30 40 51 54 55 60 61 62 70 80 90 - categories\n";
    for(int j=49;j>=0;--j)for(int n=0;n<5;n++){
        for(int i=n*10;i<(n+1)*10;i++)out<<"  "<<((i+j)%2==0?20:51)<<",";
        out<<"\n";
    }
    out<<" 1.0000 - HTFAC\n";
    for(int j=49;j>=0;--j){
        for(int i=0;i<50;++i)out<<100+i+2*j<<(i==49?"\n":",");
    }
    for(int k=0;k<6;k++){
        out<<option<<"\n";
        for(int j=49;j>=0;--j){
            for(int i=0;i<50;++i)out<<(k==0?0.1:0.2+0.02*k)<<(i==49?"\n":",");
        }
    }
    if(extra)out<<"bad extra GEO.DAT data\n";
}
int main(){
    try{
        const std::string name="p6_geo_test_fixture.txt";
        fixture(name);
        auto geo=cteas::calmet::p6::read_geo_50(name,510.885,3531.269);
        check(geo.terrain_m.size()==2500&&geo.lai.size()==2500,
              "GEO fields shape");
        check(geo.terrain_m[0]==100&&geo.terrain_m[2499]==247,
              "READGE north/south row orientation");
        check(geo.landuse[0]==20&&geo.landuse[1]==51,
              "READGE landuse integer and i-fastest");
        check(geo.z0_m[0]>0,"roughness valid");
        bool caught=false;
        try{(void)cteas::calmet::p6::read_geo_50(name,475.0,3515.436);}
        catch(const std::runtime_error&){caught=true;}
        check(caught,"historic 2023 SW corner accepted");
        fixture(name,"LCC     ");
        caught=false;
        try{(void)cteas::calmet::p6::read_geo_50(name,510.885,3531.269);}
        catch(const std::runtime_error&){caught=true;}
        check(caught,"unsupported projection accepted");
        fixture(name,"UTM     "," 0 - default z0");
        caught=false;
        try{(void)cteas::calmet::p6::read_geo_50(name,510.885,3531.269);}
        catch(const std::runtime_error&){caught=true;}
        check(caught,"unsupported default geo branch accepted");
        fixture(name,"UTM     "," 2 - gridded",100);
        caught=false;
        try{(void)cteas::calmet::p6::read_geo_50(name,510.885,3531.269);}
        catch(const std::runtime_error&){caught=true;}
        check(caught,"wrong grid size accepted");
        fixture(name,"UTM     "," 2 - gridded",50,true);
        caught=false;
        try{(void)cteas::calmet::p6::read_geo_50(name,510.885,3531.269);}
        catch(const std::runtime_error&){caught=true;}
        check(caught,"unexpected trailing data accepted");
        std::remove(name.c_str());
        std::cout<<"PASS P6C_GEO_SCOPED_SOFTWARE_ONLY\n";
        return 0;
    }catch(const std::exception& e){
        std::cerr<<"P6C_GEO_FAIL "<<e.what()<<'\n';
        return 1;
    }
}
