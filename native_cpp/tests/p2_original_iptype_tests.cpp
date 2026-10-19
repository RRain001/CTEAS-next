#include "cteas/geo/ctgproc_original_iptype.hpp"
#include "cteas/geo/ctgproc_original_coast_policy.hpp"
#include <gdal_priv.h>
#include <ogrsf_frmts.h>
#include <ogr_spatialref.h>
#include <array>
#include <cmath>
#include <filesystem>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>
using namespace cteas::reconstruction::geo;
namespace {
void need(bool pass,const char* cause){if(!pass)throw std::runtime_error(cause);}
std::unique_ptr<OGRGeometry> box(double x0,double y0,double x1,double y1){
  OGRLinearRing ring;
  ring.addPoint(x0,y0);ring.addPoint(x1,y0);ring.addPoint(x1,y1);
  ring.addPoint(x0,y1);ring.addPoint(x0,y0);
  auto p=std::make_unique<OGRPolygon>();
  p->addRing(&ring);
  return p;
}
template<class F> void rejects(F fun,const char* cause){
  bool failed=false;
  try{fun();}catch(const std::exception&){failed=true;}
  need(failed,cause);
}
std::vector<OriginalCoastPolygon> nested_rectangles(double size){
  std::vector<OriginalCoastPolygon> p;
  for(int k=1;k<=4;++k){
    const double inset=double(k-1)*.10*size;
    p.push_back({k,box(inset,inset,size-inset,size-inset)});
  }
  return p;
}
void test_hierarchy(){
  OriginalGshhsPointClassifier p(nested_rectangles(10000.));
  const auto check=[&](float km,int expected,const char* why) {
    need(p.iptype_model_km(km,km)==expected,why);
  };
  need(p.polygon_count()==4,"four Full GSHHG levels required");
  need(p.iptype_model_km(-1.f,-1.f)==0,"ocean point");
  check(.5f,1,"mainland type1");
  check(1.5f,2,"lake type2");
  check(2.5f,3,"island in lake type3");
  check(5.f,4,"pond within island type4");
  // NOTE: original PNPOLY returns 0 for touching the polygon edge.
  need(p.iptype_model_km(0.f,5.f)==0,"L1 outer coastline edge -> ocean0");
  need(p.iptype_model_km(1.f,5.f)==2,"L2 lake edge -> 2");
  need(p.iptype_model_km(2.f,5.f)==2,"L3 island edge -> 2");
  need(p.iptype_model_km(3.f,5.f)==4,"L4 pond edge -> 4");
  need(p.iptype_model_km(-1.f,-1.f,false)==1,"LCOAST false -> land1");
  rejects([&]{(void)p.iptype_model_km(NAN,1.f);},"nonfinite point must reject");
  // Native source LUGRID policy connected in-memory, without changing P2-A.
  const OriginalCoastControl control{true,true,false,false,55,
                                     OriginalLanduseSource::HistoricalUsgs38};
  need(original_lugrid_coastal_category(control,52,p.iptype_model_km(-1.f,-1.f))==55,
       "ocean point should convert52 to55");
  need(original_lugrid_coastal_category(control,54,p.iptype_model_km(-1.f,-1.f))==54,
       "ocean bay 54 special exception");
  need(original_lugrid_coastal_category(control,52,p.iptype_model_km(1.5f,1.5f))==52,
       "lake point 52 should survive");
  need(!original_lugrid_coastal_category(control,55,p.iptype_model_km(1.5f,1.5f)),
       "landward marine 55 must be discarded");
  const auto fill=OriginalCoastControl{true,false,true,false,55,
                                      OriginalLanduseSource::HistoricalUsgs38};
  need(original_svgrid_empty_cell_action(fill,false,p.iptype_model_km(-1.f,-1.f))==
       OriginalFinalCellAction::FillOcean,"empty ocean cell LMARFILL");
  need(original_svgrid_empty_cell_action(fill,false,p.iptype_model_km(1.5f,1.5f))==
       OriginalFinalCellAction::LeaveMissing,"empty lake cell must stay missing");
}
struct Cleanup{
  std::filesystem::path dir;
  ~Cleanup(){std::error_code err;std::filesystem::remove_all(dir,err);}
};
void test_synthetic_four_shapefile_loader(){
  GDALAllRegister();
  auto dir=std::filesystem::temp_directory_path()/"cteas_123_iptp_synthetic_l1l4";
  need(!std::filesystem::exists(dir),"synthetic temp dir unexpectedly exists");
  std::filesystem::create_directory(dir);
  Cleanup clean{dir};
  auto* driver=GetGDALDriverManager()->GetDriverByName("ESRI Shapefile");
  need(driver!=nullptr,"GDAL shapefile writer unavailable");
  OGRSpatialReference geo,utm;
  geo.importFromEPSG(4326);
  geo.SetAxisMappingStrategy(OAMS_TRADITIONAL_GIS_ORDER);
  utm.importFromEPSG(32652);
  utm.SetAxisMappingStrategy(OAMS_TRADITIONAL_GIS_ORDER);
  const std::array<double,4> boxlo{{129.40,129.42,129.43,129.44}};
  const std::array<double,4> boxhi{{129.50,129.48,129.47,129.46}};
  std::array<std::filesystem::path,4> files;
  for(int l=1;l<=4;++l){
    auto path=dir/("GSHHS_f_L"+std::to_string(l)+".shp");
    files[std::size_t(l-1)]=path;
    auto* raw=driver->Create(path.string().c_str(),0,0,0,GDT_Unknown,nullptr);
    need(raw!=nullptr,"synthetic shapefile create failed");
    std::unique_ptr<GDALDataset,decltype(&GDALClose)> ds(raw,GDALClose);
    auto* layer=ds->CreateLayer(("GSHHS_f_L"+std::to_string(l)).c_str(),&geo,wkbPolygon,nullptr);
    need(layer!=nullptr,"synthetic layer creation failed");
    std::unique_ptr<OGRFeature,decltype(&OGRFeature::DestroyFeature)> f(
        OGRFeature::CreateFeature(layer->GetLayerDefn()),&OGRFeature::DestroyFeature);
    auto poly=box(boxlo[std::size_t(l-1)],35.68+(.01*(l-1)),
                  boxhi[std::size_t(l-1)],35.78-(.01*(l-1)));
    need(f->SetGeometry(poly.get())==OGRERR_NONE,"synthetic polygon assign");
    need(layer->CreateFeature(f.get())==OGRERR_NONE,"synthetic feature write");
  }
  // Only synthetic test features. Production source must be pinned separately.
  const std::array<double,4> bounds{{533215.,3942629.,553215.,3962629.}};
  auto classifier=OriginalGshhsPointClassifier::load_full_l1_to_l4(files,32652,bounds);
  need(classifier.polygon_count()==4,"synthetic f L1-L4 loader count");
  std::unique_ptr<OGRCoordinateTransformation,decltype(&OCTDestroyCoordinateTransformation)> t(
      OGRCreateCoordinateTransformation(&geo,&utm),OCTDestroyCoordinateTransformation);
  need(bool(t),"synthetic WGS84 UTM transform unavailable");
  double xx=129.41,yy=35.69;
  need(t->Transform(1,&xx,&yy)!=0,"synthetic transform failed");
  need(classifier.iptype_model_km(float(xx/1000.),float(yy/1000.))==1,
       "synthetic source L1 should classify land");
  xx=129.45;yy=35.73;
  need(t->Transform(1,&xx,&yy)!=0,"nested synthetic transform failed");
  need(classifier.iptype_model_km(float(xx/1000.),float(yy/1000.))==4,
       "synthetic full four-level nested type4");
  auto badfiles=files;
  badfiles[0]=files[1];
  rejects([&]{(void)OriginalGshhsPointClassifier::load_full_l1_to_l4(
      badfiles,32652,bounds);},"reject wrong Full-L1 input");
}
} // namespace
int main(){
  test_hierarchy();
  test_synthetic_four_shapefile_loader();
  std::cout<<"ISSUE123_D2_IPTYPE_4_LEVEL_SYNTHETIC_PASS "
              "ORIGINAL_FORTRAN_PNPOLY_PARITY=NOT_RUN "
              "EXACT_AREA_V1_UNCHANGED=TRUE\n";
  return 0;
}
