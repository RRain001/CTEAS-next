// Issue #53 P2-B: GLC_FCS30D 35 -> USGS92 38 using GSHHS Full L1 land mask.
// This is a SOURCE/ENGINEERING output, not original MAKEGEO / CALMET science acceptance.
#include "cteas/geo/glc_area_fractions.hpp"
#include "cteas/geo/glcc_raw_fractions.hpp"
#include "cteas/geo/grid_origin.hpp"
#include <cpl_json.h>
#include <gdal_priv.h>
#include <ogrsf_frmts.h>
#include <ogr_spatialref.h>
#include <openssl/evp.h>
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
namespace {
namespace fs=std::filesystem;
using namespace cteas::reconstruction::geo;
constexpr const char* kSchema="cteas.p2b.glc35_usgs38_user_selected_mapping.v1";
using Features=std::array<double,38>;
void need(bool b,const char* why){if(!b)throw std::runtime_error(why);}
std::string hash(const fs::path& file){
  std::ifstream in(file,std::ios::binary);need(bool(in),"P2B_INPUT_MISSING");
  std::unique_ptr<EVP_MD_CTX,decltype(&EVP_MD_CTX_free)> ctx(EVP_MD_CTX_new(),EVP_MD_CTX_free);
  need(bool(ctx)&&EVP_DigestInit_ex(ctx.get(),EVP_sha256(),nullptr)==1,"P2B_SHA_INIT");
  std::array<char,65536> buf{};
  while(in){in.read(buf.data(),std::streamsize(buf.size()));const auto n=in.gcount();
    if(n)need(EVP_DigestUpdate(ctx.get(),buf.data(),std::size_t(n))==1,"P2B_SHA_UPDATE");}
  need(in.eof(),"P2B_SHA_READ");
  unsigned char digest[EVP_MAX_MD_SIZE]{};unsigned n=0;
  need(EVP_DigestFinal_ex(ctx.get(),digest,&n)==1&&n==32,"P2B_SHA_FINISH");
  std::string s;const char* hex="0123456789abcdef";
  for(unsigned i=0;i<n;++i){s+=hex[digest[i]>>4];s+=hex[digest[i]&15];}return s;
}
void file(const fs::path& path,const std::string& expected){
  need(expected.size()==64,"P2B_SHA_FORMAT");
  for(const char c:expected)need((c>='0'&&c<='9')||(c>='a'&&c<='f'),"P2B_SHA_LOWER_HEX");
  need(!fs::is_symlink(fs::symlink_status(path))&&fs::is_regular_file(path),
       "P2B_FILE_MISSING_OR_SYMLINK");
  need(hash(path)==expected,"P2B_INPUT_SHA_MISMATCH");
}
int integer(const char* s){std::size_t n=0;const int v=std::stoi(s,&n);need(n==std::string(s).size(),"P2B_BAD_INT");return v;}
double decimal(const char* s){std::size_t n=0;const double v=std::stod(s,&n);
  need(n==std::string(s).size()&&std::isfinite(v),"P2B_BAD_REAL");return v;}
int index38(int id) {
  auto b=kGlccUsgs92Classes.begin(),e=kGlccUsgs92Classes.end();
  auto f=std::find(b,e,id);
  need(f!=e,"P2B_UNKNOWN_USGS_CLASS");
  return int(f-b);
}
std::vector<int> policy_map(const fs::path& path){
  CPLJSONDocument d;need(d.Load(path.string()),"P2B_POLICY_JSON_INVALID");
  const auto root=d.GetRoot();
  need(root.GetString("schema","")==kSchema,"P2B_POLICY_SCHEMA");
  need(root.GetString("decision","")=="USER_SELECTED_34_FIXED_CLASSES_AND_GLC210_L1_LAND_TO_52_SEA_TO_55","P2B_POLICY_WATER_DECISION");
  need(!root.GetBool("production_authorized",true),"P2B_POLICY_SCIENCE_STATUS_INVALID");
  const auto entries=root.GetArray("fixed_classes");
  need(entries.IsValid()&&entries.Size()==34,"P2B_FIXED_CLASS_COUNT");
  std::vector<int> ret(256,-1);
  for(const auto& elem:entries) {
    const int glc=elem.GetInteger("glc_code",-1),usgs=elem.GetInteger("usgs_code",-1);
    need(glc>=0&&glc<256&&glc!=210&&ret[std::size_t(glc)]<0,"P2B_POLICY_DUPLICATE_GLC");
    (void)index38(usgs);ret[std::size_t(glc)]=usgs;
  }
  const auto water=root.GetArray("conditional_classes");
  need(water.IsValid()&&water.Size()==1,"P2B_POLICY_CONDITIONAL_COUNT");
  const auto w=water[0];
  need(w.GetInteger("glc_code",-1)==210,"P2B_POLICY_WATER_CODE");
  const auto outcomes=w.GetArray("outcomes");
  need(outcomes.IsValid()&&outcomes.Size()==2&&
      outcomes[0].GetInteger("usgs_code",-1)==52&&
      outcomes[1].GetInteger("usgs_code",-1)==55,
      "P2B_POLICY_WATER_52_55_REQUIRED");
  const auto source=root.GetObj("source_authentication");
  need(source.IsValid()&&source.GetString("selected_resolution","")=="f"&&
       source.GetString("primary_land_sea_polygon","")=="GSHHS_shp/f/GSHHS_f_L1.shp"&&
       !source.GetBool("wdbii_required_for_binary_water_split",true),
       "P2B_POLICY_GSHHS_FULL_ONLY");
  constexpr std::array<int,35> source_codes={{10,11,12,20,51,52,61,62,71,72,81,82,
    91,92,120,121,122,130,140,150,152,153,181,182,183,184,185,186,187,
    190,200,201,202,210,220}};
  for(int glc:source_codes)if(glc!=210)need(ret[std::size_t(glc)]>=0,"P2B_POLICY_INCOMPLETE");
  need(ret[183]==77&&ret[184]==77,"P2B_POLICY_USER_OVERRIDE_DRIFT");
  return ret;
}
using G=std::unique_ptr<OGRGeometry>;
using Dataset=std::unique_ptr<GDALDataset,decltype(&GDALClose)>;
using Transform=std::unique_ptr<OGRCoordinateTransformation,decltype(&OCTDestroyCoordinateTransformation)>;
G rectangle(double x0,double y0,double x1,double y1){
  need(x1>x0&&y1>y0,"P2B_EMPTY_POLYGON");
  auto p=std::make_unique<OGRPolygon>();
  OGRLinearRing ring;
  ring.addPoint(x0,y0);ring.addPoint(x1,y0);ring.addPoint(x1,y1);
  ring.addPoint(x0,y1);ring.addPoint(x0,y0);
  p->addRing(&ring);
  return G(p.release());
}
G land_geometry(const fs::path& shp,const P2Grid& grid,int epsg){
  GDALAllRegister();
  need(shp.filename()=="GSHHS_f_L1.shp","P2B_SHORELINE_NOT_FULL_L1");
  need(OGRGeometryFactory::haveGEOS(),"P2B_GEOS_REQUIRED");
  Dataset ds(static_cast<GDALDataset*>(GDALOpenEx(shp.string().c_str(),
      GDAL_OF_VECTOR|GDAL_OF_READONLY,nullptr,nullptr,nullptr)),GDALClose);
  need(bool(ds)&&ds->GetLayerCount()==1,"P2B_GSHHS_L1_OPEN");
  auto* layer=ds->GetLayer(0);
  need(layer&&layer->GetGeomType()!=wkbLineString&&layer->GetGeomType()!=wkbMultiLineString,
       "P2B_SHORELINE_MUST_BE_POLYGONS");
  OGRSpatialReference geo,dest;
  geo.SetAxisMappingStrategy(OAMS_TRADITIONAL_GIS_ORDER);
  dest.SetAxisMappingStrategy(OAMS_TRADITIONAL_GIS_ORDER);
  need(geo.importFromEPSG(4326)==OGRERR_NONE&&dest.importFromEPSG(epsg)==OGRERR_NONE,
       "P2B_CRS_INVALID");
  auto* srs=layer->GetSpatialRef();
  need(srs&&srs->IsSame(&geo),"P2B_GSHHS_MUST_BE_WGS84");
  Transform to_utm(OGRCreateCoordinateTransformation(&geo,&dest),OCTDestroyCoordinateTransformation);
  Transform to_geo(OGRCreateCoordinateTransformation(&dest,&geo),OCTDestroyCoordinateTransformation);
  need(bool(to_utm)&&bool(to_geo),"P2B_SHORELINE_TRANSFORM");
  const double x0=grid.x0_m,y0=grid.y0_m,x1=x0+grid.dx_m*grid.nx,y1=y0+grid.dx_m*grid.ny;
  // This production code handles bounded local UTM domains only, never Antarctic or antimeridian.
  std::array<double,4> xs{{x0,x1,x1,x0}},ys{{y0,y0,y1,y1}};
  double a=180,b=-180,c=90,d=-90;
  for(int q=0;q<4;++q) {
    need(bool(to_geo->Transform(1,&xs[q],&ys[q])),"P2B_UTM_TO_GEO");
    need(ys[q]>-60.&&ys[q]<85.,"P2B_ANTARCTICA_OR_POLAR_UNSUPPORTED");
    a=std::min(a,xs[q]);b=std::max(b,xs[q]);c=std::min(c,ys[q]);d=std::max(d,ys[q]);
  }
  need(b-a<5.&&d-c<5.,"P2B_BOUNDING_REGION_OR_DATELINE_UNSUPPORTED");
  layer->SetSpatialFilterRect(a-.1,c-.1,b+.1,d+.1);
  const auto domain=rectangle(x0,y0,x1,y1);
  G land;
  layer->ResetReading();
  while(auto* raw=layer->GetNextFeature()) {
    std::unique_ptr<OGRFeature,decltype(&OGRFeature::DestroyFeature)> feature(raw,&OGRFeature::DestroyFeature);
    auto* fg=feature->GetGeometryRef();
    need(fg&&fg->IsValid(),"P2B_GSHHS_INVALID_POLYGON");
    const auto t=wkbFlatten(fg->getGeometryType());
    need(t==wkbPolygon||t==wkbMultiPolygon,"P2B_GSHHS_NOT_POLYGON");
    G geom(fg->clone());
    need(geom->transform(to_utm.get())==OGRERR_NONE,"P2B_GSHHS_REPROJECT");
    G overlap(geom->Intersection(domain.get()));
    need(bool(overlap),"P2B_GSHHS_INTERSECTION_FAILED");
    if(overlap->IsEmpty())continue;
    if(!land){land=std::move(overlap);continue;}
    G uni(land->Union(overlap.get()));
    need(bool(uni)&&uni->IsValid(),"P2B_GSHHS_UNION_FAILED");
    land=std::move(uni);
  }
  // A valid fully offshore site has no selected terrestrial polygons.
  return land;
}
double assign_water(const fs::path& tif,const P2Grid& grid,int epsg,const OGRGeometry* land,
                    const std::vector<double>& raw_water,std::vector<Features>& out){
  Dataset ds(static_cast<GDALDataset*>(GDALOpenEx(tif.string().c_str(),
      GDAL_OF_RASTER|GDAL_OF_READONLY,nullptr,nullptr,nullptr)),GDALClose);
  need(bool(ds),"P2B_REOPEN_GLC_TIFF_FAILED");
  auto* band=ds->GetRasterBand(1);
  need(bool(band),"P2B_MISSING_GLC_BAND");
  auto* srs=ds->GetSpatialRef();
  OGRSpatialReference target;target.SetAxisMappingStrategy(OAMS_TRADITIONAL_GIS_ORDER);
  need(target.importFromEPSG(epsg)==OGRERR_NONE&&srs&&srs->IsSame(&target),"P2B_TIFF_CRS_DRIFT");
  double gt[6]{};
  need(ds->GetGeoTransform(gt)==CE_None&&gt[1]==30&&gt[5]==-30&&
       gt[2]==0&&gt[4]==0,"P2B_TIFF_GRID_DRIFT");
  const double gx0=grid.x0_m,gy0=grid.y0_m,gx1=gx0+grid.nx*grid.dx_m,gy1=gy0+grid.ny*grid.dx_m;
  const int width=ds->GetRasterXSize(),height=ds->GetRasterYSize();
  const int c0=std::max(0,int(std::floor((gx0-gt[0])/30.)));
  const int c1=std::min(width,int(std::ceil((gx1-gt[0])/30.)));
  const int r0=std::max(0,int(std::floor((gt[3]-gy1)/30.)));
  const int r1=std::min(height,int(std::ceil((gt[3]-gy0)/30.)));
  need(c1>c0&&r1>r0,"P2B_NO_WATER_COVERAGE");
  std::vector<std::uint8_t> pixels(std::size_t(c1-c0));
  std::vector<double> area(out.size(),0.);
  double inland=0.;
  for(int r=r0;r<r1;++r){
    need(band->RasterIO(GF_Read,c0,r,c1-c0,1,pixels.data(),c1-c0,1,
                       GDT_Byte,0,0,nullptr)==CE_None,"P2B_GLC_WATER_READ");
    const double py1=gt[3]-r*30.,py0=py1-30.;
    for(int c=c0;c<c1;++c)if(pixels[std::size_t(c-c0)]==210){
      const double px0=gt[0]+c*30.,px1=px0+30.;
      const int i0=std::max(0,int(std::floor((px0-gx0)/grid.dx_m)));
      const int i1=std::min(int(grid.nx),int(std::ceil((px1-gx0)/grid.dx_m)));
      const int j0=std::max(0,int(std::floor((py0-gy0)/grid.dx_m)));
      const int j1=std::min(int(grid.ny),int(std::ceil((py1-gy0)/grid.dx_m)));
      for(int j=j0;j<j1;++j)for(int i=i0;i<i1;++i){
        const double xlo=std::max(px0,gx0+i*grid.dx_m),xhi=std::min(px1,gx0+(i+1)*grid.dx_m);
        const double ylo=std::max(py0,gy0+j*grid.dx_m),yhi=std::min(py1,gy0+(j+1)*grid.dx_m);
        if(xhi<=xlo||yhi<=ylo)continue;
        const auto cell=std::size_t(j)*grid.nx+std::size_t(i);
        const double a=(xhi-xlo)*(yhi-ylo);
        double terrestrial=0.;
        if(land){
          const auto piece=rectangle(xlo,ylo,xhi,yhi);
          if(land->Intersects(piece.get())){
            G intersect(land->Intersection(piece.get()));
            need(bool(intersect)&&intersect->IsValid(),"P2B_COAST_INTERSECTION_FAILED");
            terrestrial=intersect->get_Area();
          }
        }
        need(std::isfinite(terrestrial)&&terrestrial>=-1e-7&&terrestrial<=a+1e-7,
             "P2B_COAST_AREA_OUTSIDE_PIXEL");
        terrestrial=std::clamp(terrestrial,0.,a);
        out[cell][std::size_t(index38(52))]+=terrestrial;
        out[cell][std::size_t(index38(55))]+=a-terrestrial;
        area[cell]+=a;inland+=terrestrial;
      }
    }
  }
  for(std::size_t cell=0;cell<out.size();++cell)
    need(std::abs(area[cell]-raw_water[cell])<std::max(1e-7,raw_water[cell]*1e-9),
         "P2B_WATER_PIECE_AREA_DRIFT");
  return inland;
}
std::string header(int epsg,int nx,int ny,const std::string& x,const std::string& y,double dk){
  std::ostringstream o;
  o<<std::left<<std::setw(16)<<"LU.DAT"<<std::setw(16)<<"2.1"
    <<"Coordinate parameters and LandUse categories\n"
    <<"   2\n"
    <<"Produced by CTEAS P2-B GLC35 GSHHS Full 52/55; SCIENCE NOT_RUN\n"
    <<"Original MAKEGEO P3 scientific equivalence NOT_RUN\n"
    <<"FRACTION\nUTM\n  "<<epsg%100<<(epsg<=32660?"N":"S")<<"\nWGS-84  02-21-2003\n"
    <<std::right<<std::setw(8)<<nx<<std::setw(8)<<ny
    <<std::fixed<<std::setprecision(3)
    <<std::setw(12)<<three_decimal_origin_km(x)
    <<std::setw(12)<<three_decimal_origin_km(y)
    <<std::setw(12)<<dk<<std::setw(12)<<dk<<std::setw(6)<<38<<"\nKM  M\n";
  for(int id:kGlccUsgs92Classes)o<<std::setw(6)<<id;
  o<<"\n";return o.str();
}
} // namespace
int main(int argc,char** argv){
  if(argc!=14){
    std::cerr<<"usage: cteas_p2_glc_lu_dat TIFF TIFF_SHA256 GSHHS_f_L1.shp SHP_SHA256"
       " POLICY_JSON POLICY_SHA256 NEW_OUT_DIR EPSG XREFKM YREFKM DGRIDKM NX NY\n";return 2;
  }
  try{
    const fs::path tif=argv[1],shore=argv[3],policy=argv[5],dest=argv[7];
    file(tif,argv[2]);file(shore,argv[4]);file(policy,argv[6]);
    need(!fs::exists(dest)&&!fs::is_symlink(fs::symlink_status(dest)),"P2B_OUTPUT_EXISTS");
    const int epsg=integer(argv[8]);
    need((epsg>=32601&&epsg<=32660)||(epsg>=32701&&epsg<=32760),
         "P2B_WGS84_UTM_REQUIRED");
    const std::string xref=argv[9],yref=argv[10];
    const double x=three_decimal_origin_km(xref)*1000.,y=three_decimal_origin_km(yref)*1000.;
    const double dk=decimal(argv[11]);const int nx=integer(argv[12]),ny=integer(argv[13]);
    need(dk>=.001&&dk<=100.&&std::abs(dk*1000.-std::round(dk*1000.))<1e-8,
         "P2B_GRID_SPACING_NOT_LU_REPRESENTABLE");
    need(nx>0&&ny>0&&std::int64_t(nx)*ny<=250000,"P2B_GRID_BUDGET");
    P2Grid grid{x,y,dk*1000.,std::size_t(nx),std::size_t(ny)};
    const auto map=policy_map(policy);
    const auto raw=compute_glc_area_fractions(tif.string(),grid,epsg);
    const auto land=land_geometry(shore,grid,epsg);
    std::vector<Features> values(grid.nx*grid.ny);
    std::vector<double> water(values.size(),0.);
    need(raw.raw_codes.size()==35,"P2B_NOT_35_RAW_CODES");
    for(std::size_t k=0;k<35;++k){
      const int glc=raw.raw_codes[k];
      for(std::size_t cell=0;cell<values.size();++cell){
        const double a=raw.area_m2[cell*35+k];
        if(glc==210)water[cell]+=a;
        else values[cell][std::size_t(index38(map[std::size_t(glc)]))]+=a;
      }
    }
    const double inland=assign_water(tif,grid,epsg,land.get(),water,values);
    for(std::size_t cell=0;cell<values.size();++cell){
      double sum=0;
      for(double v:values[cell]){need(v>=0&&std::isfinite(v),"P2B_INVALID_USGS_AREA");sum+=v;}
      need(std::abs(sum-raw.valid_m2[cell])<=std::max(1e-7,raw.valid_m2[cell]*1e-9),
           "P2B_USGS_AREA_NOT_CONSERVED");
    }
    fs::create_directory(dest);
    try{
      std::ofstream out(dest/"lu.dat",std::ios::binary);
      need(bool(out),"P2B_LU_CREATE");
      out<<header(epsg,nx,ny,xref,yref,dk);
      double largest=0.,round_error=0.;
      for(std::size_t cell=0;cell<values.size();++cell){
        out<<std::right<<std::setw(5)<<(cell%grid.nx+1)<<std::setw(5)<<(cell/grid.nx+1);
        double sum=0.,printed=0.;
        for(double area:values[cell]){
          const double f=area/raw.valid_m2[cell];
          sum+=f;
          std::ostringstream token;token<<std::fixed<<std::setprecision(3)<<f;
          out<<" "<<std::setw(5)<<token.str();
          printed+=std::stod(token.str());
        }
        need(std::abs(sum-1.)<1e-9,"P2B_FRACTION_NOT_CONSERVED");
        need(printed>=.98&&printed<=1.02,"P2B_PRINTED_FRACTION_NOT_CONSERVED");
        largest=std::max(largest,std::abs(sum-1.));
        round_error=std::max(round_error,std::abs(printed-1.));
        out<<"   .\n";
      }
      out.close();need(bool(out),"P2B_LU_WRITE");
      std::ofstream meta(dest/"p2_b_d3_manifest.json");
      need(bool(meta),"P2B_MANIFEST_CREATE");
      meta<<"{\n  \"producer\": \"cteas_p2_glc_lu_dat\",\n"
          <<"  \"source_kind\": \"GLC_FCS30D_35_TO_USGS38_GSHHS_F_L1\",\n"
          <<"  \"glc_tif_sha256\": \""<<argv[2]<<"\",\n"
          <<"  \"gshhs_l1_shp_sha256\": \""<<argv[4]<<"\",\n"
          <<"  \"mapping_policy_sha256\": \""<<argv[6]<<"\",\n"
          <<"  \"lu_dat_sha256\": \""<<hash(dest/"lu.dat")<<"\",\n"
          <<"  \"n_cells\": "<<values.size()<<", \"n_usgs_classes\": 38,\n"
          <<"  \"usgs52_inland_water_area_m2\": "<<std::setprecision(17)<<inland<<",\n"
          <<"  \"usgs55_ocean_water_area_m2\": "
            <<std::accumulate(water.begin(),water.end(),0.)-inland<<",\n"
          <<"  \"max_fraction_sum_error\": "<<largest<<",\n"
          <<"  \"max_lu_rounding_sum_error\": "<<round_error<<",\n"
          <<"  \"gshhg_distribution\": \"FULL_F_GSHHS_L1_POLYGONS\",\n"
          <<"  \"gshhg_zip_sha256_verification\": \"NOT_RUN_IN_THIS_CLI\",\n"
          <<"  \"evidence_status\": \"PRODUCED_UNVERIFIED\",\n"
          <<"  \"original_makegeo_38_to_14_parity\": \"NOT_RUN\",\n"
          <<"  \"p3_geo_dat\": \"NOT_RUN\"\n}\n";
      meta.close();need(bool(meta),"P2B_MANIFEST_WRITE");
    }catch(...){fs::remove_all(dest);throw;}
    std::cout<<"P2B_GLC35_USGS38_LU_DAT=PRODUCED_UNVERIFIED CELLS="<<values.size()
             <<" INLAND_WATER_M2="<<inland<<" P3=NOT_RUN\n";
    return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}
}
