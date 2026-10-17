#!/usr/bin/env python3
"""G28 selected source G26B original AVEMIX->WSTARR Fortran parity.

Original unchanged CALMET AVEMIX L2104-2355 and WSTARR L36884-36950
are compiled. Their real independent inputs are C++ upstream G26B
post-MIXHT/pre-AVEMIX ZI/ZICONV and source G26A DIAGNO winds/QH/T/rho.
Do NOT feed native output ZI/ZICONV into the original input driver.
Scope: one G19 2SS+2US first hour with synthetic source observations,
NOT original whole COMP or multi-station CALMET.DAT 45-field parity.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,subprocess,tempfile
from pathlib import Path
from compare_original_similt_profile import VENDOR_BLOB
ROOT=Path(__file__).resolve().parents[4]
VENDOR=ROOT/"engine/vendor/src/CALMET_v6.5.0_L150223"
# New STAGE-specific comparison gates, not original full-hour 45 fields.
TOL_ZI_M=0.02
TOL_ZICONV_M=0.02
TOL_WSTAR_MPS=0.0002

DRIVER="""      program g28_literal_source_comp
      include 'params.met'
      real u(mxnx,mxny),v(mxnx,mxny),zi(mxnx,mxny)
      real ziconv(mxnx,mxny),qh(mxnx,mxny),temp(mxnx,mxny)
      real rho(mxnx,mxny),wstar(mxnx,mxny)
      integer land(mxnx,mxny),nx,ny,mnmdav,iwat1,iwat2
      integer ilevzi
      character*256 input,output
      call get_command_argument(1,input)
      call get_command_argument(2,output)
      open(10,file=trim(input),status='old')
      read(10,*) nx,ny,mnmdav,hafang,dgrid,iwat1,iwat2,
     1           ilevzi
      if(nx.ne.12.or.ny.ne.12.or.dgrid.ne.10000.)stop 92
      if(mnmdav.ne.1.or.ilevzi.ne.1)stop 93
      do j=1,ny
        do i=1,nx
          read(10,*)u(i,j),v(i,j),zi(i,j),ziconv(i,j),
     1          qh(i,j),temp(i,j),rho(i,j),land(i,j)
          if(land(i,j).ge.iwat1.and.land(i,j).le.iwat2)
     1         stop 94
        enddo
      enddo
      close(10)
      do j=1,ny
        do i=1,nx
          wstar(i,j)=0.
        enddo
      enddo
      call avemix(nx,ny,mnmdav,hafang,dgrid,u,v,zi,ziconv)
      call wstarr(ziconv,qh,temp,rho,land,iwat1,iwat2,
     1            nx,ny,wstar)
      open(11,file=trim(output),status='replace')
      do j=1,ny
        do i=1,nx
          write(11,'(2(I4,1X),3(ES23.14E3,1X))')
     1            i,j,zi(i,j),ziconv(i,j),wstar(i,j)
        enddo
      enddo
      close(11)
      end
"""

def literal_sources(temp:Path):
    data=(VENDOR/"calmet.for").read_bytes()
    sha=hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
    if sha!=VENDOR_BLOB:
        raise RuntimeError("G28 original frozen Fortran CALMET blob drift")
    lines=data.decode().splitlines(keepends=True)
    anchors=[
        ("avemix","      subroutine avemix(","      subroutine avetmp(",2104,2356),
        ("wstarr","      subroutine wstarr(","      subroutine xmit(",36884,36951),
    ]
    refs={};routines=[]
    for name,start,end,first,after in anchors:
        begins=[i for i,l in enumerate(lines) if l.lower().startswith(start)]
        ends=[i for i,l in enumerate(lines) if l.lower().startswith(end)]
        if len(begins)!=1 or len(ends)!=1 or begins[0]+1!=first or ends[0]+1!=after:
            raise RuntimeError(f"G28 original literal {name} source boundary drift")
        dest=temp/f"original_{name}.for"
        dest.write_text("".join(lines[begins[0]:ends[0]]))
        refs[name]={"start":first,"end_inclusive":after-1,
                    "sha256":hashlib.sha256(dest.read_bytes()).hexdigest()}
        routines.append(dest)
    return routines,{"original_vendor_blob":sha,"original_subroutines":refs}


def parse_source(path:Path):
    lines=path.read_text().splitlines()
    if len(lines)!=145:
        raise ValueError("G28 selected original source has not 144 grid cells")
    h=lines[0].split()
    if len(h)!=8 or [int(h[i]) for i in (0,1,2,5,6,7)][:3]!=[12,12,1]:
        raise ValueError("G28 source grid/readcf controls missing")
    nx,ny,mnmdav=map(int,h[:3])
    half=float(h[3]);grid=float(h[4]);iw1=int(h[5]);iw2=int(h[6]);ilev=int(h[7])
    if grid!=10000 or ilev!=1 or not math.isfinite(half) or half<=0 or half>=90:
        raise ValueError("G28 G26B source selected IAVEZI/ILEVZI unsupported")
    qh_positive=0
    for row in lines[1:]:
        x=row.split()
        if len(x)!=8:raise ValueError("G28 first-hour eight independent inputs absent")
        z=[float(v) for v in x[:7]]
        land=int(x[7])
        if not all(map(math.isfinite,z)) or z[2]<0 or z[3]<0 or (
            z[5]<180 or z[5]>350 or z[6]<=0 or iw1<=land<=iw2):
            raise ValueError("G28 G26B MIXHT/DIAGNO input contains invalid source physics")
        qh_positive+=z[4]>0
    return {"nx":nx,"ny":ny,"mnmdav":mnmdav,"hafang_deg":half,
            "dgrid_m":grid,"ilevzi":ilev,
            "positive_qh_cells":qh_positive}


def native_grid(path:Path):
    with path.open(newline="") as file:
        rows=list(csv.DictReader(file))
    if len(rows)!=144:
        raise ValueError("G28 C++ AVEMIX WSTAR first-hour output shape !=144")
    arr={}
    for x in rows:
        i,j=int(x["i"]),int(x["j"])
        value=(float(x["zi_after_avemix_m"]),
               float(x["ziconv_after_avemix_m"]),
               float(x["wstar_mps"]))
        if (i,j) in arr or not 1<=i<=12 or not 1<=j<=12 or (
            not all(map(math.isfinite,value))):
            raise ValueError("G28 duplicate or nonfinite source COMP candidate")
        arr[(i,j)]=value
    return arr


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--mode",choices=("Debug","Release"),required=True)
    ap.add_argument("--source-prefix",type=Path,required=True)
    ap.add_argument("--require-convection",action="store_true")
    ap.add_argument("--out",type=Path,required=True)
    a=ap.parse_args()
    source=Path(str(a.source_prefix)+".source.input")
    meta=parse_source(source)
    cpp=native_grid(Path(str(a.source_prefix)+".native.csv"))
    with tempfile.TemporaryDirectory(prefix="p6g-g28-literal-avemix-") as tmp:
        work=Path(tmp)
        src,proof=literal_sources(work)
        driver=work/"original_comp_driver.for"
        driver.write_text(DRIVER)
        exe=work/"g28_vendor"
        opt="-O0" if a.mode=="Debug" else "-O2"
        comp=subprocess.run([
            "gfortran",opt,"-std=legacy","-fno-automatic",
            "-ffixed-line-length-none","-fallow-argument-mismatch",
            "-I"+str(VENDOR),*[str(p) for p in src],str(driver),
            "-o",str(exe)
        ],capture_output=True,text=True)
        if comp.returncode:
            raise RuntimeError("G28 vendor AVEMIX/WSTARR compile failed: "+
                               comp.stderr[-4200:])
        output=work/"original-comp-144.txt"
        proc=subprocess.run([str(exe),str(source),str(output)],
                            capture_output=True,text=True)
        if proc.returncode:
            raise RuntimeError("G28 original AVEMIX/WSTARR runtime failed: "+
                               proc.stderr[-1500:]+proc.stdout[-800:])
        lines=output.read_text().splitlines()
    if len(lines)!=144:
        raise RuntimeError("G28 literal original COMP output missing grid cells")
    maxima=[0.,0.,0.]
    diffs=[]
    ref_positive_w=0
    for line in lines:
        vals=line.split()
        if len(vals)!=5:raise ValueError("G28 original cell columns malformed")
        i,j=int(vals[0]),int(vals[1])
        key=(i,j)
        if key not in cpp:raise ValueError("G28 original (i,j) mismatch")
        originals=tuple(map(float,vals[2:]))
        if not all(map(math.isfinite,originals)):
            raise ValueError("G28 original vendor nonfinite ZI/ZICONV/WSTAR")
        ref_positive_w+=originals[2]>1.e-5
        for idx,(v,c,tol) in enumerate(zip(originals,cpp[key],
                                           (TOL_ZI_M,TOL_ZICONV_M,TOL_WSTAR_MPS))):
            d=abs(v-c)
            maxima[idx]=max(maxima[idx],d)
            if d>tol:diffs.append([i,j,idx,v,c,d,tol])
    info={
        "scope":"literal original AVEMIX then WSTARR on G26B pre-AVEMIX source MIXHT grids",
        "weather":"synthetic observations in original met.inp/GEO/SURF/UP",
        "mode":a.mode,
        "vendor_source":proof,"independent_source":meta,
        "compared_scalar_values":432,
        "original_nonzero_wstar_cells":ref_positive_w,
        "max_abs":{"zi_m":maxima[0],"ziconv_m":maxima[1],"wstar_mps":maxima[2]},
        "stage_gate":{"zi_m":TOL_ZI_M,"ziconv_m":TOL_ZICONV_M,
                      "wstar_mps":TOL_WSTAR_MPS},
        "errors":diffs[:25],
        "full_vendor_comp_accepted":False,
        "full_multistation_45_field":False,
    }
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(info,indent=2)+"\n")
    if diffs or (a.require_convection and (
        meta["positive_qh_cells"]<=0 or ref_positive_w<=0)):
        raise AssertionError(f"G28 literal original AVEMIX WSTARR source mismatch "
                             f"errors={diffs[:6]} positive_wstar={ref_positive_w}")
    print(f"PASS_P6G_G28_LITERAL_ORIGINAL_AVEMIX_WSTARR mode={a.mode} "
          f"cells=144 fields=432 positive_wstar={ref_positive_w} "
          f"max_abs={info['max_abs']} MULTISTATION_45_FIELD=NOT_ACCEPTED")


if __name__=="__main__":
    main()
