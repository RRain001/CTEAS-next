// Issue #160 C4: modern 30m ORIGINAL_STYLE_POINT_SAMPLING, not P2-B areas.
// No historical GLCC mapping or vendor source used by this executable.
#include "cteas/geo/glc30m_point_sampling.hpp"
#include "cteas/geo/ctgproc_original_sampling_lu_writer.hpp"
#include <cpl_json.h>
#include <gdal_priv.h>
#include <ogrsf_frmts.h>
#include <ogr_spatialref.h>
#include <openssl/evp.h>
#include <array>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>
namespace {
namespace fs=std::filesystem;
using namespace cteas::reconstruction::geo;
void need(bool v,const char* msg){if(!v)throw std::runtime_error(msg);}
std::string hash(const fs::path& file){
  std::ifstream stream(file,std::ios::binary);
  need(bool(stream),"P2C_SOURCE_HASH_FILE_MISSING");
  std::unique_ptr<EVP_MD_CTX,decltype(&EVP_MD_CTX_free)> md(EVP_MD_CTX_new(),EVP_MD_CTX_free);
  need(bool(md)&&EVP_DigestInit_ex(md.get(),EVP_sha256(),nullptr)==1,
       "P2C_SHA_CTX_INIT");
  std::array<char,65536> chunk{};
  while(stream){
    stream.read(chunk.data(),std::streamsize(chunk.size()));
    if(stream.gcount())
      need(EVP_DigestUpdate(md.get(),chunk.data(),std::size_t(stream.gcount()))==1,
           "P2C_SHA_UPDATE");
  }
  need(stream.eof(),"P2C_SHA_SOURCE_IO");
  std::array<unsigned char,EVP_MAX_MD_SIZE> result{};
  unsigned size=0;
  need(EVP_DigestFinal_ex(md.get(),result.data(),&size)==1&&size==32,
       "P2C_SHA_FINAL");
  const char* hex="0123456789abcdef";std::string str;
  for(unsigned i=0;i<size;++i){str+=hex[result[i]>>4];str+=hex[result[i]&15];}
  return str;
}
void regular(const fs::path& p){
  need(fs::is_regular_file(p)&&!fs::is_symlink(fs::symlink_status(p)),
       "P2C_SOURCE_MISSING_OR_SYMLINK");
}
std::map<int,int> selected_map(const fs::path& file){
  CPLJSONDocument doc;
  need(doc.Load(file.string()),"P2C_INVALID_USER_POLICY_JSON");
  const auto r=doc.GetRoot();
  need(r.GetString("schema")=="cteas.p2b.glc35_usgs38_user_selected_mapping.v1"&&
       r.GetString("decision")=="USER_SELECTED_34_FIXED_CLASSES_AND_GLC210_L1_LAND_TO_52_SEA_TO_55"&&
       r.GetString("output_contract")=="USGS92_38_CLASS_LU_DAT_V2_1"&&
       !r.GetBool("legacy_p2a_modified")&&
       !r.GetBool("p3_makegeo_modified"),
       "P2C_FROZEN_USER_POLICY_DRIFT");
  const auto arr=r.GetArray("fixed_classes");
  need(arr.Size()==34,"P2C_POLICY_NOT_34_FIXED_CLASSES");
  std::map<int,int> mapping;
  for(int i=0;i<arr.Size();++i){
    const auto row=arr[i];const int glc=row.GetInteger("glc_code",0);
    const int usgs=row.GetInteger("usgs_code",0);
    need(glc!=210&&glc>0&&usgs>0&&mapping.emplace(glc,usgs).second,
         "P2C_POLICY_DUPLICATE_OR_INVALID_MAPPING");
  }
  const auto conditional=r.GetArray("conditional_classes");
  need(conditional.Size()==1&&conditional[0].GetInteger("glc_code")==210&&
       conditional[0].GetArray("outcomes").Size()==2&&
       conditional[0].GetArray("outcomes")[0].GetInteger("usgs_code")==52&&
       conditional[0].GetArray("outcomes")[1].GetInteger("usgs_code")==55,
       "P2C_POLICY_WATER_210_NOT_FULL_L1_52_55");
  need(r.GetObj("source_authentication").GetString("selected_resolution")=="f",
       "P2C_GSHHG_FULL_NOT_SELECTED");
  return mapping;
}
using Dataset=std::unique_ptr<GDALDataset,decltype(&GDALClose)>;
using Transform=std::unique_ptr<OGRCoordinateTransformation,decltype(&OCTDestroyCoordinateTransformation)>;
struct LandPolygons {
  std::vector<std::unique_ptr<OGRGeometry>> land;
  std::vector<OGREnvelope> envelopes;
  bool contains(double x,double y)const{
    const OGRPoint p(x,y);
    for(std::size_t k=0;k<land.size();++k){
      const auto& b=envelopes[k];
      if(x>=b.MinX&&x<=b.MaxX&&y>=b.MinY&&y<=b.MaxY&&
         land[k]->Contains(&p))return true;
    }
    return false;
  }
};
LandPolygons read_full_l1(const fs::path& path,int epsg,const P2Grid& grid){
  GDALAllRegister();
  need(path.filename()=="GSHHS_f_L1.shp","P2C_ONLY_FULL_F_L1_ALLOWED");
  need(hash(path)=="121435427911ea80624802e0f352d777eaf6ba6966ca5f07e687650e95329fd9",
       "P2C_FULL_L1_SOURCE_SHA_DRIFT");
  for(const auto* ext:{".shx",".dbf",".prj"}){
    auto q=path;q.replace_extension(ext);regular(q);
  }
  Dataset src(static_cast<GDALDataset*>(GDALOpenEx(path.string().c_str(),
              GDAL_OF_VECTOR,nullptr,nullptr,nullptr)),GDALClose);
  need(bool(src)&&src->GetLayerCount()>=1,
       "P2C_GSHHG_FULL_L1_OPEN");
  auto* layer=src->GetLayer(0);
  need(layer!=nullptr&&layer->GetSpatialRef()!=nullptr&&
       OGRGeometryFactory::haveGEOS(),"P2C_GSHHG_FULL_L1_GEOMETRY");
  OGRSpatialReference src_crs,model;
  src_crs=*layer->GetSpatialRef();
  src_crs.SetAxisMappingStrategy(OAMS_TRADITIONAL_GIS_ORDER);
  model.SetAxisMappingStrategy(OAMS_TRADITIONAL_GIS_ORDER);
  need(model.importFromEPSG(epsg)==OGRERR_NONE,
       "P2C_GSHHG_FULL_L1_PROJECTED_CRS");
  Transform to_utm(OGRCreateCoordinateTransformation(&src_crs,&model),
                   OCTDestroyCoordinateTransformation);
  Transform to_geo(OGRCreateCoordinateTransformation(&model,&src_crs),
                   OCTDestroyCoordinateTransformation);
  need(bool(to_utm)&&bool(to_geo),"P2C_GSHHG_CRS_CONVERSION");
  double llx=grid.x0_m-100.,lly=grid.y0_m-100.;
  double urx=grid.x0_m+grid.nx*grid.dx_m+100.;
  double ury=grid.y0_m+grid.ny*grid.dx_m+100.;
  need(to_geo->Transform(1,&llx,&lly)!=0&&
       to_geo->Transform(1,&urx,&ury)!=0,
       "P2C_GSHHG_MODEL_BBOX_TRANSFORM");
  layer->SetSpatialFilterRect(std::min(llx,urx),std::min(lly,ury),
                              std::max(llx,urx),std::max(lly,ury));
  layer->ResetReading();
  LandPolygons out;
  while(auto* raw=layer->GetNextFeature()){
    std::unique_ptr<OGRFeature,decltype(&OGRFeature::DestroyFeature)> feature(
        raw,OGRFeature::DestroyFeature);
    const auto* geometry=feature->GetGeometryRef();
    if(!geometry)continue;
    std::unique_ptr<OGRGeometry> poly(geometry->clone());
    need(bool(poly)&&poly->transform(to_utm.get())==OGRERR_NONE,
         "P2C_GSHHG_FULL_L1_TRANSFORM_FAIL");
    OGREnvelope box;poly->getEnvelope(&box);
    out.envelopes.push_back(box);
    out.land.push_back(std::move(poly));
    need(out.land.size()<10000,"P2C_GSHHG_UNBOUNDED_POLYGON_SET");
  }
  need(!out.land.empty(),"P2C_NO_REAL_FULL_L1_LAND_POLYGON_IN_DOMAIN");
  return out;
}
} // namespace
int main(int argc,char** argv){
  // Site, 2022 b23 source, frozen user mapping, official GSHHG Full L1
  // shp (or dash for inland), fresh output directory. No coastline for Hefei.
  if(argc!=6){
    std::cerr<<"usage: cteas_p2_glc30m_point_lu "
               "hefei|wolsong GLC2022_30M.tif POLICY.json "
               "GSHHS_f_L1.shp|- NEW_OUTPUT_DIR\n";
    return 2;
  }
  try{
    const std::string site=argv[1];
    need(site=="hefei"||site=="wolsong","P2C_SITE_NOT_REVIEWED");
    const bool inland=site=="hefei";
    const fs::path tif=argv[2],policy=argv[3],shore=argv[4],dest=argv[5];
    regular(tif);regular(policy);
    need(!fs::exists(dest)&&!fs::is_symlink(fs::symlink_status(dest)),
         "P2C_OUTPUT_COLLISION");
    need(inland?shore.string()=="-":shore.string()!="-",
         "P2C_LCOAST_POLICY_FOR_SITE");
    const auto mapping=selected_map(policy);
    GDALAllRegister();
    Dataset src(static_cast<GDALDataset*>(GDALOpenEx(
            tif.string().c_str(),GDAL_OF_RASTER|GDAL_OF_READONLY,
            nullptr,nullptr,nullptr)),GDALClose);
    need(bool(src),"P2C_REAL_30M_TIFF_REQUIRED");
    const int epsg=inland?32650:32652;
    const P2Grid grid{
        inland?503385.:533215.,inland?3523769.:3942629.,100.,200,200};
    const auto tif_sha=hash(tif);
    const auto policy_sha=hash(policy);
    // Previous authentic Wolsong 20km source is immutable; unreviewed
    // Hefei 20km input must satisfy complete envelope and categorical tests
    // and be separately SHA-admitted by its metadata/audit.
    if(!inland)
      need(tif_sha=="2a1a208c5386735692d788066f730c7391e87f0981e7b9ad099442af2e217711",
           "P2C_WOLSONG_FROZEN_2022_SOURCE_SHA_DRIFT");
    std::unique_ptr<LandPolygons> land;
    if(!inland){
      regular(shore);
      land=std::make_unique<LandPolygons>(read_full_l1(shore,epsg,grid));
    }
    Glc30mSamplingStats st{};
    const IsGshhgFullLandPoint classify=land?
       IsGshhgFullLandPoint([&land](double x,double y){
         return land->contains(x,y);
       }):IsGshhgFullLandPoint{};
    const auto hits=sample_glc30m_original_mesh(
        *src,grid,epsg,mapping,10,classify,inland,st);
    fs::create_directory(dest);
    try{
      std::ofstream lu(dest/"lu.dat",std::ios::binary);
      need(bool(lu),"P2C_30M_OUTPUT_LU_CREATE");
      const auto lu_status=write_original_sampling_lu(
          lu,hits,false,inland?50:52,
          "CTEAS P2-C 30m ORIGINAL_STYLE_POINT_SAMPLING (#160)",
          "GLC_FCS30D 2022 b23 / GSHHG Full L1 only; not EXACT_AREA_V1");
      lu.close();need(bool(lu),"P2C_30M_OUTPUT_LU_WRITE");
      need(lu_status.total_hits==st.included_subpoints&&
           lu_status.missing_cells==st.missing_cells&&
           lu_status.fraction_fields==1520000,
           "P2C_30M_LU_HITS_CONSERVATION");
      std::ofstream csv(dest/"hits.csv");
      need(bool(csv),"P2C_30M_HITS_FILE_CREATE");
      csv<<"i,j,samples";
      for(int code:kGlccUsgs92Classes)csv<<",cat"<<code;
      csv<<"\n";
      for(std::size_t j=0;j<grid.ny;++j)
        for(std::size_t i=0;i<grid.nx;++i){
          const auto idx=j*grid.nx+i;
          csv<<i+1<<","<<j+1<<","<<hits.samples[idx];
          std::uint64_t total=0;
          for(std::size_t k=0;k<38;++k){
            const auto n=hits.counts[idx*38+k];
            csv<<","<<n;total+=n;
          }
          need(total==hits.samples[idx],"P2C_30M_INDEPENDENT_HITS_REQUIRED");
          csv<<"\n";
        }
      csv.close();need(bool(csv),"P2C_30M_HITS_WRITE");
      std::ofstream meta(dest/"sampling_manifest.json");
      need(bool(meta),"P2C_30M_META_CREATE");
      meta<<"{\n"
          <<"  \"method\": \"P2_C_GLC30M_ORIGINAL_STYLE_POINT_SAMPLING\",\n"
          <<"  \"site\": \""<<site<<"\", \"epsg\": "<<epsg<<",\n"
          <<"  \"nx\": 200, \"ny\": 200, \"step_m\": 100, \"mesh\": 10,\n"
          <<"  \"tif_sha256\": \""<<tif_sha<<"\",\n"
          <<"  \"user_mapping_sha256\": \""<<policy_sha<<"\",\n"
          <<"  \"full_l1_shp_sha256\": \""<<(inland?"NOT_APPLICABLE":hash(shore))<<"\",\n"
          <<"  \"lu_dat_sha256\": \""<<hash(dest/"lu.dat")<<"\",\n"
          <<"  \"hits_csv_sha256\": \""<<hash(dest/"hits.csv")<<"\",\n"
          <<"  \"source_pixels\": "<<st.source_pixels<<",\n"
          <<"  \"invalid_source_pixels\": "<<st.invalid_source_pixels<<",\n"
          <<"  \"generated_subpoints\": "<<st.generated_subpoints<<",\n"
          <<"  \"invalid_subpoints\": "<<st.invalid_subpoints<<",\n"
          <<"  \"outside_subpoints\": "<<st.outside_subpoints<<",\n"
          <<"  \"included_subpoints\": "<<st.included_subpoints<<",\n"
          <<"  \"water52_hits\": "<<st.water52_hits<<",\n"
          <<"  \"water55_hits\": "<<st.water55_hits<<",\n"
          <<"  \"missing_cells\": "<<st.missing_cells<<",\n"
          <<"  \"independent_40k_x_38_oracle\": \"NOT_RUN\",\n"
          <<"  \"p3_lu_format_independent\": \"NOT_RUN\",\n"
          <<"  \"p3_original_makegeo_physics\": \"OUT_OF_SCOPE_ISSUE46\"\n"
          <<"}\n";
      meta.close();need(bool(meta),"P2C_30M_META_WRITE");
      std::cout<<"P2C_30M_CANDIDATE_LU_PRODUCED"
               <<" site="<<site<<" hits="<<st.included_subpoints
               <<" missing="<<st.missing_cells
               <<" p3=NOT_RUN independent_hitsch=NOT_RUN\n";
    }catch(...){fs::remove_all(dest);throw;}
    return 0;
  }catch(const std::exception& e){
    std::cerr<<"P2C_30M_FAIL_CLOSED:"<<e.what()<<"\n";
    return 2;
  }
}
