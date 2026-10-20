#!/usr/bin/env python3
"""Independent literal original CALMET VERTAV + PREPDI on actual 1US NOAA UP.

Consumes the genuine source-file-backed G19/READ62 upper sounding bytes
decoded by the *existing* native G19 decoder. Independently compiles unmodified
CALMET VERTAV and PREPDI source math against those RAW decoded wind levels.
Verifies upper k=1 IEXTRP=-4 missing policy. No G23/INTER2 execution.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import compare_original_vertav as vertav
import compare_original_prepdi_time as prepdi

NZ=9
TOL_VERTAV=2e-4  # accepted original VERTAV selected reference tolerance
TOL_PREPDI=3e-4  # accepted original PREPDI selected reference tolerance

VERTAV_DRIVER=r"""      program p6b2c_original_upper
      include 'params.met'
      real uu(mxus,mxlev),vv(mxus,mxlev),zz(mxus,mxlev)
      real zface(mxnzp1),uave(mxnz),vave(mxnz)
      integer n,k,nprofiles,nlev,i
      character*256 inp,out
      call get_command_argument(1,inp)
      call get_command_argument(2,out)
      open(10,file=trim(inp),status='old')
      open(11,file=trim(out),status='replace')
      read(10,*)nprofiles
      if(nprofiles.ne.2)stop 91
      read(10,*)(zface(i),i=1,10)
      do n=1,nprofiles
        read(10,*)nlev
        if(nlev.lt.2.or.nlev.gt.mxlev)stop 92
        do i=1,nlev
          read(10,*)zz(1,i),uu(1,i),vv(1,i)
        enddo
        call vertav(1,uu,vv,zz,nlev,9,zface,uave,vave)
        do k=1,9
          write(11,'(2(I4,1X),2(ES22.13E3,1X))')
     1      n,k,uave(k),vave(k)
        enddo
      enddo
      close(10)
      close(11)
      end
"""

def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def run(command:list[str],cwd:Path)->str:
    p=subprocess.run(list(map(str,command)),cwd=cwd,capture_output=True,text=True)
    if p.returncode:
        raise RuntimeError("original CALMET independent compiled source rc="
                           +str(p.returncode)+" stderr="+p.stderr[-1100:]
                           +" stdout="+p.stdout[-1100:])
    return p.stdout

def parse_input(path:Path)->dict:
    if not path.is_file() or path.is_symlink():
        raise ValueError("P6-B2C real NOAA sounding-stage missing/nonregular")
    with path.open() as f:
        if f.readline().strip()!="P6B2C_ORIGINAL_1US_PREPDI_STAGE_V1":
            raise ValueError("P6-B2C source provenance schema mismatch")
        site=f.readline().split()
        if len(site)!=8 or site[0]!="SITE":
            raise ValueError("P6-B2C real upper site/time/source header invalid")
        _,station,clock,old,new,delta,togo,iextrp=site
        station,clock,old,new,delta,togo,iextrp=map(int,(station,clock,old,new,delta,togo,iextrp))
        if (station<=0 or delta!=43200 or iextrp!=-4 or not old<clock<new
                or new-old!=delta or new-clock!=togo or not 0<togo<delta):
            raise ValueError("P6-B2C actual original 00/12 source time invalid")
        z=f.readline().split()
        if len(z)!=11 or z[0]!="ZFACE":
            raise ValueError("P6-B2C original face layer source invalid")
        zface=list(map(float,z[1:]))
        if zface[0]!=0 or any(not math.isfinite(v) for v in zface) or any(
            b<=a for a,b in zip(zface,zface[1:])):
            raise ValueError("P6-B2C non-monotonic/invalid original ZFACE")
        soundings=[]
        for site_index in range(2):
            h=f.readline().split()
            if len(h)!=3 or h[:2]!=["SOUNDING",str(site_index)]:
                raise ValueError("P6-B2C original actual source sounding identity")
            n=int(h[2])
            if not 2<=n<=99:
                raise ValueError("P6-B2C actual source sounding number unsupported")
            data=[]
            for _ in range(n):
                row=f.readline().split()
                if len(row)!=3:
                    raise ValueError("P6-B2C true sounding level malformed")
                val=tuple(map(float,row))
                if not all(map(math.isfinite,val)):
                    raise ValueError("P6-B2C actual observed NOAA layer nonfinite")
                # Identical C++ VERTAV missing wind filter, not a new sounding.
                if abs(val[1])<998.99 and abs(val[2])<998.99:
                    data.append(val)
            if len(data)<2 or any(b[0]<=a[0] for a,b in zip(data,data[1:])):
                raise ValueError("P6-B2C actual sounding lacks valid increasing height wind data")
            soundings.append(data)
        t=f.readline().split()
        if t!=["NATIVE","9"]:
            raise ValueError("P6-B2C real source missing existing native upper candidate")
        native=[]
        for i in range(1,10):
            row=f.readline().split()
            if len(row)!=3 or int(row[0])!=i:
                raise ValueError("P6-B2C original layer ordering differs from native G20")
            uv=tuple(map(float,row[1:]))
            if not all(map(math.isfinite,uv)) or any(abs(v)>100 for v in uv):
                raise ValueError("P6-B2C native U/V invalid")
            native.append(uv)
        if f.read().strip():
            raise ValueError("P6-B2C source file contains unexpected trailing observations")
    return {"station":station,"clock":clock,"earlier":old,"later":new,
            "gap":delta,"to_go":togo,"iextrp":iextrp,
            "zface":zface,"soundings":soundings,"native":native,
            "original_hour_source_sha256":sha(path)}

def calculate(vendor:Path,stage:Path)->dict:
    values=parse_input(stage)
    if vendor.is_symlink() or not vendor.is_file():
        raise ValueError("original pinned CALMET Fortran source unavailable")
    src=vendor.read_text(encoding="latin-1").splitlines(keepends=True)
    # The exact unmodified source lines govern the INTER2 upper k=1 mask.
    if (src[14005-1].strip().lower()!="if (iextrp .le. 0) i1 = 2" or
        src[14099-1].strip().lower()!="if (iextrp .le. 0) i1=2"):
        raise ValueError("original CALMET PREPDI IEXTRP first upper-layer provenance changed")
    policy_line=src[14099-1]
    with tempfile.TemporaryDirectory(prefix="real-huoshan-original-prepdi-") as d:
        root=Path(d)
        original_vertav=root/"calmet_verbatim_vertav.for"
        vertav_proof=vertav.source_extract(vendor,original_vertav)
        vdriver=root/"p6b2c_original_vertav_driver.for"
        vdriver.write_text(VERTAV_DRIVER)
        vertav_input=root/"original_sounding_input.txt"
        with vertav_input.open("w") as out:
            out.write("2\n"+" ".join(map(str,values["zface"]))+"\n")
            for sounding in values["soundings"]:
                out.write(str(len(sounding))+"\n")
                for z,u,v in sounding:
                    out.write(f"{z:.9g} {u:.9g} {v:.9g}\n")
        vexe=root/"original_vertav"
        run(["gfortran","-O0","-std=legacy","-fno-automatic",
             "-ffixed-line-length-none","-I"+str(vendor.parent),
             original_vertav,vdriver,"-o",vexe],root)
        outpath=root/"original_vertav.txt"
        run([vexe,vertav_input,outpath],root)
        vertav_lines=outpath.read_text().splitlines()
        if len(vertav_lines)!=18:
            raise ValueError("original vendor VERTAV did not produce exact original 2x9")
        averaged=[[],[]]
        for j,line in enumerate(vertav_lines):
            row=line.split()
            if len(row)!=4 or int(row[0])!=j//9+1 or int(row[1])!=j%9+1:
                raise ValueError("original vendor VERTAV wrong two-sounding layer order")
            uv=tuple(float(x.replace("D","E")) for x in row[2:])
            if not all(map(math.isfinite,uv)):
                raise ValueError("original vendor VERTAV nonfinite")
            averaged[j//9].append(uv)
        original_prepdi=root/"calmet_verbatim_prepdi_time.for"
        prepdi_proof=prepdi.extract(vendor,original_prepdi)
        pexe=root/"original_prepdi"
        run(["gfortran","-O0","-std=legacy","-ffixed-line-length-none",
             original_prepdi,"-o",pexe],root)
        pinput=root/"original_prepdi_input.txt"
        with pinput.open("w") as out:
            out.write(f"1\n{values['gap']} {values['to_go']} 1\n")
            for older,newer in zip(*averaged):
                out.write(" ".join(str(x) for x in (*older,*newer))+"\n")
        poutput=root/"original_prepdi.txt"
        run([pexe,pinput,poutput],root)
        data=[line.split() for line in poutput.read_text().splitlines()]
        if len(data)!=9 or any(len(row)!=4 or int(row[0])!=1 or int(row[1])!=k
                               for k,row in enumerate(data,1)):
            raise ValueError("original vendor first-hour PREPDI output shape invalid")
        numeric=[tuple(float(x.replace("D","E")) for x in row[2:]) for row in data]
        # Compile literal unchanged original IEXTRP policy expression
        # separately instead of hardcoding k=1 from a C++ guess.
        policy=root/"original_prepdi_upper_k1_fortran.for"
        policy.write_text(
            "      program original_prepdi_missing_k1\n"
            "      integer iextrp,i1\n"
            "      iextrp=-4\n"
            "      i1=1\n"+policy_line+
            "      write(*,*)i1\n"
            "      end\n",encoding="latin-1")
        pbin=root/"original_i1"
        run(["gfortran","-O0","-std=legacy","-ffixed-line-length-none",
             policy,"-o",pbin],root)
        mask=int(run([pbin],root).strip())
    if mask!=2:
        raise ValueError("original CALMET IEXTRP=-4 wrongly has upper k1 present")
    maximum=0.;failed=0;samples=[]
    for k,(original,native) in enumerate(zip(numeric,values["native"]),1):
        for component,a,b in zip(("U","V"),original,native):
            err=abs(a-b);maximum=max(maximum,err)
            if err>TOL_PREPDI:
                failed+=1
                if len(samples)<10:
                    samples.append({"layer":k,"component":component,
                                    "original":a,"native":b,"error":err})
    return {
        "status":"S4_P6B2C1_TRUE_NOAA_1US_ORIGINAL_VERTAV_PREPDI_PASS_SCOPED" if failed==0
                else "S4_P6B2C1_TRUE_NOAA_1US_ORIGINAL_VERTAV_PREPDI_MISMATCH",
        "site":"REAL_HUOSHAN_ACTUAL_ORIGINAL_NOAA_IGRA_FIRST_HOUR",
        "original_station_id":values["station"],
        "original_model_end_epoch":values["clock"],
        "original_earlier_epoch":values["earlier"],
        "original_later_epoch":values["later"],
        "original_iextrp":values["iextrp"],
        "original_upper_inter2_layer_one":"MISSING_EDIT_999",
        "original_upper_inter2_valid_k":[2,3,4,5,6,7,8,9],
        "actual_bracket_seconds":values["gap"],
        "actual_sounding_valid_wind_levels":[len(v) for v in values["soundings"]],
        "original_calmet_for_sha256":vertav_proof["original_calmet_sha256"],
        "source_stage_sha256":values["original_hour_source_sha256"],
        "literal_original_vertav_source":vertav_proof,
        "literal_original_prepdi_source":prepdi_proof,
        "original_vertex_averaged_2x9_components":36,
        "original_prepdi_first_hour_compared_uv":18,
        "original_tolerance_mps":TOL_PREPDI,
        "max_abs_delta_mps":maximum,
        "failed_components":failed,
        "first_mismatches":samples,
        "native_g20_upper_inter2_fields_modified":False,
        "original_full_DIAGI_STHEOR_INTER2":False,
        "independent_original_full_CALMET_45_fields":False,
        "P6_NEW_SITE_SCIENCE":"NOT_ACCEPTED",
    }

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vendor-calmet-for",type=Path,required=True)
    parser.add_argument("--source-stage",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    x=parser.parse_args()
    try:
        r=calculate(x.vendor_calmet_for,x.source_stage)
        if x.out.exists() or x.out.is_symlink():
            raise ValueError("original PREPDI evidence must be a new file")
        x.out.parent.mkdir(parents=True,exist_ok=True)
        x.out.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n")
        print(json.dumps({"status":r["status"],"station":r["original_station_id"],
                          "original_prepdi_compared_uv":r["original_prepdi_first_hour_compared_uv"],
                          "max_abs":r["max_abs_delta_mps"],
                          "failed":r["failed_components"],
                          "k1":r["original_upper_inter2_layer_one"]}))
        return 0 if r["failed_components"]==0 else 2
    except (OSError,ValueError,RuntimeError,subprocess.CalledProcessError) as exc:
        print(json.dumps({"status":"S4_P6B2C1_TRUE_NOAA_PREPDI_FAIL_CLOSED",
                          "reason":str(exc)[:1400]}),file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
