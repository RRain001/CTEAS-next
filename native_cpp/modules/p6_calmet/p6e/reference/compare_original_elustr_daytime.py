#!/usr/bin/env python3
"""Original CALMET 6.5.0 ELUSTR daytime with verbatim PSIUD and PSIUC.
Separate independent numerical gate: 36 x 20 x 3 = 2160 scalar values.
Nighttime stable ELUSTR is separately source-verified.
"""
import argparse,hashlib,json,math,subprocess,tempfile
from pathlib import Path
BLOB="437f43bb7f0e51a1919e56664663e1a046986ed0"
CASES,NX,NY=36,5,4
ABS_QH=0.005
ABS_USTAR=0.0003
ABS_L=0.6
REL=0.00015
PARAMS="""      integer mxnx,mxny,mxss,io6
      parameter(mxnx=5,mxny=4,mxss=4,io6=6)
"""
DRIVER="""      program daytime_elustr_driver
      include 'params.met'
      real z0(mxnx,mxny),u(mxnx,mxny),v(mxnx,mxny)
      real rho(mxnx,mxny),temp(mxnx,mxny),cc(mxnx,mxny)
      real qh(mxnx,mxny),ustar(mxnx,mxny),el(mxnx,mxny)
      integer land(mxnx,mxny),near(mxnx,mxny),icc(mxss)
      integer ncases,nx,ny,c,i,j,ipsi,wl,wh
      real zm
      read(*,*)ncases,nx,ny
      if(nx.ne.5.or.ny.ne.4)stop 34
      do c=1,ncases
        read(*,*)ipsi,wl,wh,zm
        do i=1,nx
          do j=1,ny
            read(*,*)z0(i,j),u(i,j),v(i,j),rho(i,j),temp(i,j),
     1              qh(i,j),land(i,j)
            cc(i,j)=0.1
            near(i,j)=1
            ustar(i,j)=-7777.
            el(i,j)=-7777.
          enddo
        enddo
        call elustr(z0,u,v,zm,near,rho,temp,icc,land,
     1              wl,wh,nx,ny,1,cc,ipsi,qh,ustar,el)
        do i=1,nx
          do j=1,ny
            write(*,'(3(I6,1X),3(ES24.14E3,1X))')
     1          c,i,j,qh(i,j),ustar(i,j),el(i,j)
          enddo
        enddo
      enddo
      end
"""
def run(command,inp=None):
    return subprocess.run([str(v) for v in command],input=inp,text=True,
                          capture_output=True,check=True).stdout
def extract(raw):
    lines=raw.decode("utf-8").splitlines(keepends=True)
    anchors=[
        ("      subroutine elustr(", "      subroutine elustr2(",220,280),
        ("      function psiud(", "      function psitd(",35,60),
        ("      function psiuc(", "      subroutine surfvar_back(",40,60),
    ]
    collected=[];loc=[]
    for begin,end,lo,hi in anchors:
        st=[i for i,v in enumerate(lines) if v.lower().startswith(begin)]
        en=[i for i,v in enumerate(lines) if v.lower().startswith(end)]
        if len(st)!=1 or len(en)!=1 or not lo<en[0]-st[0]<hi:
            raise RuntimeError("original CALMET ELUSTR/PSIU anchors changed "+begin)
        collected.append("".join(lines[st[0]:en[0]]))
        loc.append([st[0]+1,en[0]])
    return "\n".join(collected),loc
def fixture():
    winds=(0.,0.001,0.3,0.7,1.2,2.7,6.,11.,17.)
    rough=(0.007,0.03,0.08,0.15,0.4,0.9)
    qh=(0.,0.15,3.,15.,45.,120.,360.,700.)
    temps=(268.,278.,290.,302.,315.)
    lines=[f"{CASES} {NX} {NY}"];counts={"water":0,"neutral":0,"positive":0,"psi0":0,"psi1":0}
    for c in range(CASES):
        psi=c%2
        lines.append(f"{psi} 50 60 {10.0+5.0*(c%3)}")
        counts["psi"+str(psi)]+=1
        for i in range(NX):
            for j in range(NY):
                k=i+2*j+c
                land=55 if (i+2*j+3*c)%8==0 else 12
                heat=qh[k%len(qh)]
                if land==55:counts["water"]+=1
                elif heat==0:counts["neutral"]+=1
                else:counts["positive"]+=1
                lines.append(f"{rough[k%len(rough)]} "
                    f"{winds[(i+j+c)%len(winds)]} "
                    f"{winds[(2*i+j+c)%len(winds)]*0.38:.7f} "
                    f"{1.00+0.06*((i+j+c)%7):.7f} "
                    f"{temps[(i+3*j+c)%len(temps)]} {heat} {land}")
    return "\n".join(lines)+"\n",counts
def parse(raw):
    rows=[]
    for line in raw.splitlines():
        tokens=line.split()
        if len(tokens)!=6:raise ValueError("ELUSTR daytime output schema")
        idx=tuple(int(x) for x in tokens[:3])
        nums=tuple(float(x.replace("D","E")) for x in tokens[3:])
        if not all(math.isfinite(n) for n in nums):raise ValueError("ELUSTR daytime nonfinite output")
        rows.append((idx,nums))
    if len(rows)!=CASES*NX*NY:raise ValueError("ELUSTR daytime value count")
    return rows
def main():
    p=argparse.ArgumentParser()
    for key in ("vendor","cpp","out"):p.add_argument("--"+key,required=True,type=Path)
    a=p.parse_args()
    raw=a.vendor.read_bytes()
    sha=run(["git","hash-object",a.vendor]).strip()
    if sha!=BLOB:raise RuntimeError("Unfrozen original CALMET source")
    body,loc=extract(raw)
    inp,counts=fixture()
    with tempfile.TemporaryDirectory(prefix="cteas-elustr-daytime-") as tempdir:
        d=Path(tempdir)
        for name,source in (("params.met",PARAMS),("elustr_original.for",body),("driver.for",DRIVER)):
            (d/name).write_text(source)
        run(["gfortran","-O0","-std=legacy","-fno-automatic",
             "-ffixed-line-length-none","-I"+str(d),
             d/"elustr_original.for",d/"driver.for","-o",d/"original"])
        source=parse(run([d/"original"],inp))
    native=parse(run([a.cpp],inp))
    errors=[];delta_max=[0.,0.,0.];total_fail=0
    for (key,f),(kk,v) in zip(source,native):
        if key!=kk:raise ValueError("ELUSTR daytime reordered")
        water=(f[1]==-7777. and f[2]==-7777.)
        for i in range(3):
            dif=abs(f[i]-v[i])
            delta_max[i]=max(delta_max[i],dif)
            if water and i in (1,2):
                wrong=f[i]!=v[i]
            else:
                wrong=dif>(ABS_QH,ABS_USTAR,ABS_L)[i]+REL*abs(f[i])
            if wrong:
                total_fail+=1
                if len(errors)<20:errors.append(dict(cell=key,field=i,ref=f[i],cpp=v[i],error=dif))
        if not water and (f[1]<0.05 or (f[0]>0.0 and f[2]>=0.0)):
            raise ValueError("ELUSTR daytime invalid reference physics")
    report=dict(status="PASS" if total_fail==0 else "FAIL",
                cases=CASES,grid_cells=CASES*NX*NY,
                values_compared=3*CASES*NX*NY,
                distribution=counts,max_abs_errors_qh_ustar_L=delta_max,
                frozen_abs_tolerances=[ABS_QH,ABS_USTAR,ABS_L],
                frozen_relative_tolerance=REL,
                exceedances=total_fail,first_mismatches=errors,
                original_git_blob=sha,original_sha256=hashlib.sha256(raw).hexdigest(),
                original_subroutines_line_ranges=loc,
                scope="CALMET ELUSTR QH>=0 day/neutral, both original PSIUD and PSIUC modes; no 2022 143h coupled COMP")
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    if total_fail:raise SystemExit(1)
if __name__=="__main__":main()
