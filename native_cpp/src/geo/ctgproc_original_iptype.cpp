#include "cteas/geo/ctgproc_original_iptype.hpp"
#include <ogrsf_frmts.h>
#include <ogr_spatialref.h>
#include <algorithm>
#include <array>
#include <cmath>
#include <limits>
#include <stdexcept>
#include <string>
#include <utility>
namespace cteas::reconstruction::geo {
namespace {
void require(bool ok,const char* why){if(!ok)throw std::runtime_error(why);}
using Transform=std::unique_ptr<OGRCoordinateTransformation,decltype(&OCTDestroyCoordinateTransformation)>;
using Dataset=std::unique_ptr<GDALDataset,decltype(&GDALClose)>;
using G=std::unique_ptr<OGRGeometry>;
bool polygon_geometry(const OGRGeometry* p){
  if(!p)return false;
  const auto t=wkbFlatten(p->getGeometryType());
  return t==wkbPolygon||t==wkbMultiPolygon;
}
} // namespace
OriginalGshhsPointClassifier::OriginalGshhsPointClassifier(
    std::vector<OriginalCoastPolygon> polygons):polygons_(std::move(polygons)){
  require(OGRGeometryFactory::haveGEOS(),"IPTYPE_GEOS_REQUIRED");
  for(const auto& p:polygons_){
    require(p.level>=1&&p.level<=4,"IPTYPE_LEVEL_MUST_BE_1_TO_4");
    require(polygon_geometry(p.geometry.get())&&p.geometry->IsValid(),
            "IPTYPE_MISSING_OR_INVALID_POLYGON");
  }
}
int OriginalGshhsPointClassifier::iptype_model_km(float x_km,float y_km,bool lcoast) const{
  // Exact branching in original Fortran IPTYPE: disabled coastal option -> land.
  if(!lcoast)return 1;
  if(!std::isfinite(x_km)||!std::isfinite(y_km))
    throw std::invalid_argument("IPTYPE_NONFINITE_POINT");
  OGRPoint point(double(x_km)*1000.,double(y_km)*1000.);
  int answer=0;
  for(const auto& p:polygons_){
    if(answer>=p.level)continue; // Original IPTYPE skips lower/equal priority.
    OGREnvelope e;
    p.geometry->getEnvelope(&e);
    if(point.getX()<e.MinX||point.getX()>e.MaxX||
       point.getY()<e.MinY||point.getY()>e.MaxY)continue;
    // Original PNPOLY has -1 outside, 0 edge, 1 inside. GEOS is the
    // D2 software surrogate; REAL*4 PNPOLY numerical parity remains NOT_RUN.
    if(point.Touches(p.geometry.get())){
      // Explicit original Fortran edge table:
      // L1 edge -> ocean0, L2 edge -> lake2,
      // L3 edge -> lake2, L4 edge -> pond4.
      if(p.level==1)answer=0;
      if(p.level==2||p.level==3)answer=2;
      if(p.level==4)answer=4;
    }else if(point.Within(p.geometry.get())){
      answer=std::max(answer,p.level);
    }
  }
  return answer;
}
OriginalGshhsPointClassifier OriginalGshhsPointClassifier::load_full_l1_to_l4(
    const std::array<std::filesystem::path,4>& shapefiles,
    int epsg,const std::array<double,4>& bounds){
  require((epsg>=32601&&epsg<=32660)||(epsg>=32701&&epsg<=32760),
          "IPTYPE_WGS84_UTM_ONLY");
  const auto [x0,y0,x1,y1]=bounds;
  require(std::isfinite(x0)&&std::isfinite(y0)&&std::isfinite(x1)&&std::isfinite(y1)&&
          x1>x0&&y1>y0&&x1-x0<=50000.&&y1-y0<=50000.,
          "IPTYPE_DOMAIN_MUST_BE_BOUNDED_50KM");
  GDALAllRegister();
  OGRSpatialReference geo,utm;
  geo.SetAxisMappingStrategy(OAMS_TRADITIONAL_GIS_ORDER);
  utm.SetAxisMappingStrategy(OAMS_TRADITIONAL_GIS_ORDER);
  require(geo.importFromEPSG(4326)==OGRERR_NONE&&
          utm.importFromEPSG(epsg)==OGRERR_NONE,"IPTYPE_CRS_INIT_FAILURE");
  Transform togeo(OGRCreateCoordinateTransformation(&utm,&geo),OCTDestroyCoordinateTransformation);
  Transform toutm(OGRCreateCoordinateTransformation(&geo,&utm),OCTDestroyCoordinateTransformation);
  require(bool(togeo)&&bool(toutm),"IPTYPE_TRANSFORM_FAILED");
  std::array<double,4> gx{{x0,x1,x1,x0}},gy{{y0,y0,y1,y1}};
  double lo=180,hi=-180,la=90,ha=-90;
  for(std::size_t k=0;k<4;++k){
    require(togeo->Transform(1,&gx[k],&gy[k])!=0,"IPTYPE_UTM_TO_GEO_FAILED");
    lo=std::min(lo,gx[k]);hi=std::max(hi,gx[k]);
    la=std::min(la,gy[k]);ha=std::max(ha,gy[k]);
  }
  require(hi-lo<5&&ha-la<5&&la>-60&&ha<85,
          "IPTYPE_UNREVIEWED_DATELINE_OR_POLAR_DOMAIN");
  std::vector<OriginalCoastPolygon> polygons;
  for(int level=1;level<=4;++level){
    const auto& shp=shapefiles[std::size_t(level-1)];
    const std::string expected="GSHHS_f_L"+std::to_string(level)+".shp";
    require(shp.filename()==expected,"IPTYPE_REQUIRES_GSHHG_FULL_L1_L4");
    require(!std::filesystem::is_symlink(std::filesystem::symlink_status(shp))&&
            std::filesystem::is_regular_file(shp),"IPTYPE_SOURCE_MISSING_OR_SYMLINK");
    Dataset ds(static_cast<GDALDataset*>(GDALOpenEx(shp.string().c_str(),
       GDAL_OF_VECTOR|GDAL_OF_READONLY,nullptr,nullptr,nullptr)),GDALClose);
    require(bool(ds)&&ds->GetLayerCount()==1,"IPTYPE_GSHHG_SHAPEFILE_OPEN");
    OGRLayer* lyr=ds->GetLayer(0);
    require(lyr!=nullptr,"IPTYPE_SOURCE_LAYER_MISSING");
    const OGRSpatialReference* srs=lyr->GetSpatialRef();
    require(srs&&srs->IsSame(&geo),"IPTYPE_SOURCE_MUST_BE_WGS84");
    const auto geometry_type=wkbFlatten(lyr->GetGeomType());
    require(geometry_type==wkbPolygon||geometry_type==wkbMultiPolygon,
            "IPTYPE_SOURCE_MUST_BE_POLYGON_LAYER");
    // 0.1 degree bounded geographic prefilter, not a new land/sea classifier.
    lyr->SetSpatialFilterRect(lo-.1,la-.1,hi+.1,ha+.1);
    lyr->ResetReading();
    while(OGRFeature* feat=lyr->GetNextFeature()){
      std::unique_ptr<OGRFeature,decltype(&OGRFeature::DestroyFeature)> f(
          feat,&OGRFeature::DestroyFeature);
      const OGRGeometry* src=f->GetGeometryRef();
      require(polygon_geometry(src)&&src->IsValid(),"IPTYPE_BAD_SOURCE_POLYGON");
      G projected(src->clone());
      require(projected&&projected->transform(toutm.get())==OGRERR_NONE&&
              projected->IsValid(),"IPTYPE_PROJECTION_INVALID");
      polygons.push_back({level,std::move(projected)});
      require(polygons.size()<=5000,"IPTYPE_GSHHG_POLYGON_BUDGET_EXCEEDED");
    }
  }
  // No fill or automatic ocean/land decision here. The caller must
  // independently establish that the selected source window has the
  // appropriate original COASTEXT surrounding polygon semantics.
  return OriginalGshhsPointClassifier(std::move(polygons));
}
} // namespace cteas::reconstruction::geo
