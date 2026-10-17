#!/usr/bin/env python3
"""P6D9A chained *unchanged-original* WIND1/INTER2/SMOOTH/DIVCEL/W parity.

Independently compiles frozen original routines, explicitly transmits
intermediate arrays through text fixtures and compares one-call C++ bridge.
The same chain is replayed with the original IOBR=1 tail (O'Brien W
adjustment L6153-L6159 then MINIM L6180) enabled and, separately, with the
original IFRADJ=1 Froude terrain adjustment L5643-L5644 applied to the
step-one winds before the boundary snapshot and INTER2.
This is a SYNTHETIC IDENTITY bypass of the remaining TOPOF2/slope/heat
physics; no actual Hefei 2022 U/V/W equivalence is inferred.
"""
import argparse
import csv
import hashlib
import json
import math
import subprocess
from pathlib import Path

import compare_original_wind1_firstguess as wind1
import compare_original_inter2 as inter2
import compare_original_diagno_final_segment as diag
import compare_original_diagno_obrien_minim as obr
import compare_original_diagno_d9a_fradj as fradj
import compare_original_diagno_d9a_slope as upstream
import compare_original_diagno_d9a_topof2 as kinematic

SOURCE_BLOB="437f43bb7f0e51a1919e56664663e1a046986ed0"
NX=NY=50
NZ=9
NC=NX*NY
COMP_TOL=2e-4
DZ=(20.,20.,40.,80.,160.,320.,560.,800.,1000.)
SMOOTH=(0,1,2,0,1,2,0,1,0)
RADIUS=(.05,12.,12.,12.,.6,1.5)
# Original CELLZB(1)=ZFACE(1) (m) and the original namelist MINIM controls
# NITER/DIVLIM used for the IOBR=1 replay of the same chain.
ZFACE1_M=0.
MINIM_ITERATIONS=3
MINIM_DIVLIM=0.
# Original IKINE=1 pre-blend kinematic route controls: ALPHA is the empirical
# topographic coefficient and NITER the real deck's namelist iteration cap
# (both unused by the frozen deck because it has IKINE=0). DIVLIM is set to a
# deterministic 0 so both implementations execute the same number of
# Gauss-Seidel iterations: with the deck's DIVLIM=5e-6 the original's
# convergence test (DIVMAX<=DIVLIM) is threshold-sensitive and the two runs can
# exit at different iterations. Measured: at DIVLIM=0 the calm scene agrees to
# 2.4e-06 m/s, while at DIVLIM=5e-6 the same scene spreads to 2.8e-03 m/s even
# though the two active scenes stay within 7.2e-06 m/s in both settings.
ALPHA=0.1
KINEMATIC_NITER=50
KINEMATIC_DIVLIM=0.
# Original TERSET envelope radius, the real deck's TERRAD=15 km (met.inp L604).
TERRAD_KM=15.

def run(args):
    p=subprocess.run([str(x) for x in args],capture_output=True,text=True,timeout=180)
    if p.returncode:
        raise RuntimeError("command="+repr(args)+" return="+str(p.returncode)+
                           " stdout="+p.stdout[-900:]+" stderr="+p.stderr[-2800:])

def compile_references(vendor,out):
    base=["gfortran","-O0","-std=legacy","-fno-automatic",
          "-ffixed-line-length-none","-fallow-argument-mismatch",
          "-I"+str(vendor)]
    wind_sources=wind1.extract(vendor,out)
    orig_w=out/"d9_original_wind1"
    drv_w=out/"d9_original_wind1_driver.for"
    drv_w.write_text(wind1.DRIVER)
    run(base+wind_sources+[drv_w,"-o",orig_w])

    interp_src=inter2.extract_original(vendor,out)
    orig_i=out/"d9_original_inter2"
    drv_i=out/"d9_original_inter2_driver.for"
    drv_i.write_text(inter2.DRIVER)
    run(base+[s for s,_ in interp_src]+[drv_i,"-o",orig_i])

    seg_src,block,meta=diag.original_source(vendor,out)
    orig_d=out/"d9_original_final"
    drv_d=out/"d9_original_final_driver.for"
    drv_d.write_text(diag.DRIVER_HEAD+block+diag.DRIVER_TAIL)
    run(base+[s for s,_ in seg_src]+[drv_d,"-o",orig_d])
    orig_o,obrien_meta=obr.compile_reference(vendor,out,base)
    orig_f,fradj_meta=fradj.compile_reference(vendor,out,base)
    orig_u,upstream_meta=upstream.compile_reference(vendor,out,base)
    orig_k,kinematic_meta=kinematic.compile_reference(vendor,out,base)
    return (orig_w,orig_i,orig_d,orig_o,orig_f,orig_u,orig_k),dict(
        wind1_original_sha=SOURCE_BLOB,
        inter2_original=[s for _,s in interp_src],
        final_original=meta,
        obrien_original=obrien_meta,
        fradj_original=fradj_meta,
        upstream_original=upstream_meta,
        kinematic_original=kinematic_meta)

def generate_synthetic(scene):
    name=scene["name"]
    land=[52 if (name=="upper_bias" and i<10) else 10
          for j in range(NY) for i in range(NX)]
    observation_weight=[
        0.5+0.125*((i+j+k)%3)
        for k in range(NZ) for j in range(NY) for i in range(NX)
    ]
    station_u=[
        (1.5+0.125*k if l==0 else 2.5+0.125*k)
        for k in range(NZ) for l in range(2)
    ]
    station_v=[
        (-2.0+0.0625*k if l==0 else 1.25+0.125*k)
        for k in range(NZ) for l in range(2)
    ]
    return land,observation_weight,station_u,station_v

def write_bridge(path,scene,land,weights,sta_u,sta_v,obrien=False,froude=False,
                 slope=False,kin=False,terset=False):
    planes=fradj.fields(scene)
    slope_planes=upstream.fields(scene,land)
    with path.open("w") as f:
        def line(values):
            f.write(" ".join(map(str,values))+"\n")
        line([scene["surface_x"],scene["surface_y"],
              scene["upper_x"],scene["upper_y"],scene["u"],scene["v"],
              scene["roughness"],scene["latitude"],scene["height"],
              scene["icalm"]])
        line(scene["bias"])
        for u,v in scene["upper"]:
            line([u,v])
        line(SMOOTH)
        line(DZ)
        line([2]*NZ)
        line(RADIUS)
        for row in range(0,len(land),NX):line(land[row:row+NX])
        for row in range(0,len(weights),NX):line(weights[row:row+NX])
        for k in range(NZ):line(sta_u[k*2:k*2+2])
        for k in range(NZ):line(sta_v[k*2:k*2+2])
        # Original IOBR, CELLZB(1)=ZFACE(1), NITER and DIVLIM controls, then
        # the original IFRADJ and ISLOPE selectors with their fixtures. The
        # IKINE record is last; the fixture record order is not the DIAGNO
        # call order, the C++ bridge applies the stages in source order.
        line([ZFACE1_M,1 if obrien else 0,MINIM_ITERATIONS,MINIM_DIVLIM])
        fradj.write_bridge_fields(f,1 if froude else 0,*planes)
        upstream.write_bridge_fields(f,1 if slope else 0,slope_planes,land)
        kinematic.write_bridge_fields(f,1 if kin else 0,ALPHA,KINEMATIC_NITER,
                                        KINEMATIC_DIVLIM)
        f.write(f"{1 if terset else 0} {TERRAD_KM:.9f}\n")

def read_original_wind(path):
    rows=[line.split() for line in path.read_text().splitlines()]
    if len(rows)!=NC*NZ:raise RuntimeError("WIND1 original shape wrong")
    u=[];v=[]
    for idx,row in enumerate(rows):
        expected=(idx%NX+1,(idx//NX)%NY+1,idx//NC+1)
        if len(row)!=5 or tuple(map(int,row[:3]))!=expected:
            raise RuntimeError("WIND1 original record order invalid")
        u.append(float(row[3]))
        v.append(float(row[4]))
    return u,v

def write_original_inter2(ref_input,scene,land,weights,values,guess):
    # Use the unchanged INTER2 driver exactly as the independently
    # source-verified comparison script does; step1 comes from original WIND1.
    data=(scene["name"],2,False,list(RADIUS),[2]*NZ,
          [scene["surface_x"]*0.001,scene["upper_x"]*0.001],
          [scene["surface_y"]*0.001,scene["upper_y"]*0.001],
          land,values,guess,weights)
    inter2.write_input(ref_input,data)

def read_inter2_output(path):
    rows=path.read_text().splitlines()
    if len(rows)!=NC*NZ:raise RuntimeError("INTER2 output shape")
    x=[]
    for n,line in enumerate(rows):
        p=line.split()
        if len(p)!=4 or tuple(map(int,p[:3]))!=(
                n%NX+1,(n//NX)%NY+1,n//NC+1):
            raise RuntimeError("INTER2 grid ordering")
        x.append(float(p[3]))
    return x

def original_boundaries(u,v):
    ub=[];vb=[]
    for k in range(NZ):
        for side in range(2):
            i=0 if side==0 else NX-1
            ub.extend(u[k*NC+j*NX+i] for j in range(NY))
    for k in range(NZ):
        for side in range(2):
            j=0 if side==0 else NY-1
            vb.extend(v[k*NC+j*NX+i] for i in range(NX))
    return ub,vb

def compare_blend(u,v,modern):
    with modern.open(newline="") as f:rows=list(csv.DictReader(f))
    if len(rows)!=NC*NZ:raise RuntimeError("D9A C++ blended output dimensions")
    errors=[];largest=0.;changed=0
    for n,row in enumerate(rows):
        expected=(n%NX+1,(n//NX)%NY+1,n//NC+1)
        if tuple(int(row[k]) for k in ("i","j","k"))!=expected:
            raise RuntimeError("D9A blended grid mismatch")
        for name,orig in (("u",u[n]),("v",v[n])):
            val=float(row[name])
            if not math.isfinite(val):raise RuntimeError("nonfinite C++ blended field")
            error=abs(orig-val)
            largest=max(largest,error)
            if error>COMP_TOL and len(errors)<12:
                errors.append(dict(ijk=expected,component=name,error=error))
    return dict(components_compared=2*NC*NZ,
                max_abs_error_mps=largest,
                first_errors=errors,status="PASS" if not errors else "FAIL")

def main():
    p=argparse.ArgumentParser()
    for arg in ("vendor","cpp","out"):
        p.add_argument("--"+arg,type=Path,required=True)
    args=p.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    raw=(args.vendor/"calmet.for").read_bytes()
    sha=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
    if sha!=SOURCE_BLOB:raise RuntimeError("Original vendor CALMET source changed")
    (original_wind,original_inter,original_final,original_obrien,
     original_fradj,original_upstream,original_kinematic),meta=(
        compile_references(args.vendor,args.out))
    results={}
    # Independent original first guess, then two independent INTER2
    # components, then actual original final DIAGNO SMOOTH/DIVCEL/W block.
    selected={"unbiased","upper_bias","calm_icalm0"}

    def original_tail(folder,tag,first_u,first_v):
        """Original INTER2 U/V plus the literal L6119-L6148 segment.

        ``first_u``/``first_v`` are the step-one grid winds the original
        DIAGNO would carry into the L5748 WINDBC snapshot and L6055/L6059
        INTER2 calls.
        """
        observed={}
        for comp,values,first in (("u",station_u,first_u),("v",station_v,first_v)):
            config=folder/("inter2"+tag+"."+comp+".inp")
            dest=folder/("inter2"+tag+"."+comp+".original")
            write_original_inter2(config,scene,land,weights,values,first)
            run([original_inter,config,dest])
            observed[comp]=read_inter2_output(dest)
        bc_u,bc_v=original_boundaries(first_u,first_v)
        case=folder/("final"+tag+".original.inp")
        segment=folder/("final"+tag+".original")
        bounds=folder/("boundary"+tag+".original")
        diag.write_case(case,list(SMOOTH),[
            observed["u"],observed["v"],bc_u,bc_v])
        run([original_final,case,segment,bounds])
        return observed,bc_u,bc_v,segment,bounds,case

    for scene in wind1.scenes():
        name=scene["name"]
        if name not in selected:continue
        folder=args.out/name
        folder.mkdir(exist_ok=True)
        land,weights,station_u,station_v=generate_synthetic(scene)
        planes=fradj.fields(scene)
        inp=folder/"bridge.in"
        write_bridge(inp,scene,land,weights,station_u,station_v)
        ref_w=folder/"wind1.original"
        cpp_w=folder/"wind1.cpp"
        cpp_blend=folder/"blend.cpp.csv"
        cpp_final=folder/"final.cpp.csv"
        cpp_bc=folder/"boundary.cpp"
        cpp_prepared=folder/"prepared.cpp.csv"
        # The one-call C++ run never reads original output files.
        run([args.cpp,inp,cpp_w,cpp_blend,cpp_final,cpp_bc,cpp_prepared,
             folder/"w_faces.disabled.csv"])
        run([original_wind,inp,ref_w])
        comparison_first=wind1.compare(ref_w,cpp_w,name)
        u,v=read_original_wind(ref_w)

        observed,bc_u,bc_v,original_d,original_bc,original_d_in=original_tail(
            folder,"",u,v)
        comparison_blend=compare_blend(observed["u"],observed["v"],cpp_blend)
        comparison_final=diag.compare(original_d,cpp_final,original_bc,cpp_bc)
        # Same chain replayed with the original IOBR=1 tail (O'Brien W
        # adjustment L6153-L6159 then MINIM L6180). The C++ side must reach
        # the identical final U/V/DIV/W and WINDBC boundaries.
        obrien_inp=folder/"bridge.obrien.in"
        write_bridge(obrien_inp,scene,land,weights,station_u,station_v,True)
        cpp_final_obrien=folder/"final.obrien.cpp.csv"
        cpp_bc_obrien=folder/"boundary.obrien.cpp"
        cpp_prepared_obrien=folder/"prepared.obrien.cpp.csv"
        run([args.cpp,obrien_inp,folder/"wind1.obrien.cpp",
             folder/"blend.obrien.cpp.csv",cpp_final_obrien,cpp_bc_obrien,
             cpp_prepared_obrien,folder/"w_faces.disabled.csv"])
        obrien_in=folder/"obrien.original.inp"
        obrien_out=folder/"obrien.original"
        obrien_bc=folder/"obrien.boundary.original"
        obr.write_case(obrien_in,list(SMOOTH),
                       [observed["u"],observed["v"],bc_u,bc_v],
                       ZFACE1_M,1,MINIM_ITERATIONS,MINIM_DIVLIM)
        run([original_obrien,obrien_in,obrien_out,obrien_bc])
        comparison_obrien=diag.compare(obrien_out,cpp_final_obrien,
                                       obrien_bc,cpp_bc_obrien)
        # Original IOBR=1 must cancel every top W face; the IOBR=0 replay of
        # the same scene must keep at least one.
        comparison_obrien["original_iobr1_top_face_nonzero_cells"]=(
            obr.top_face_nonzero(obrien_out))
        comparison_obrien["original_iobr0_top_face_nonzero_cells"]=(
            obr.top_face_nonzero(original_d))
        # Original IFRADJ=1 route L5643-L5644: the literal FRADJ rotates the
        # step-one UG/VG before the L5748 boundary snapshot, the L6055/L6059
        # INTER2 calls and the L6119-L6148 segment. C++ must match both the
        # adjusted step-one field and the resulting final field.
        terrain,highest,lapse,temperature=planes
        fradj_in=folder/"fradj.original.inp"
        fradj_out=folder/"fradj.original"
        fradj.write_case(fradj_in,ZFACE1_M,DZ,terrain,highest,lapse,
                         temperature,u,v)
        run([original_fradj,fradj_in,fradj_out])
        step_u,step_v=fradj.read_output(fradj_out)
        froude_inp=folder/"bridge.froude.in"
        write_bridge(froude_inp,scene,land,weights,station_u,station_v,
                     froude=True)
        cpp_prepared_froude=folder/"prepared.froude.cpp.csv"
        cpp_final_froude=folder/"final.froude.cpp.csv"
        cpp_bc_froude=folder/"boundary.froude.cpp"
        run([args.cpp,froude_inp,folder/"wind1.froude.cpp",
             folder/"blend.froude.cpp.csv",cpp_final_froude,cpp_bc_froude,
             cpp_prepared_froude,folder/"w_faces.disabled.csv"])
        comparison_froude_step=fradj.compare(fradj_out,cpp_prepared_froude,u,v)
        f_observed,f_bc_u,f_bc_v,f_segment,f_bounds,_=original_tail(
            folder,".froude",step_u,step_v)
        comparison_froude=diag.compare(f_segment,cpp_final_froude,
                                       f_bounds,cpp_bc_froude)
        comparison_froude["original_froude_adjusted_components"]=(
            comparison_froude_step["original_adjusted_components"])
        comparison_froude["froude_step_max_abs_errors"]=(
            comparison_froude_step["max_abs_errors"])
        # INTER2 blend on the Froude-corrected step one must also match.
        comparison_froude_blend=compare_blend(
            f_observed["u"],f_observed["v"],folder/"blend.froude.cpp.csv")
        # Real-deck upstream combination: literal FRADJ L5643-L5644 then
        # literal SLOPE L5722-L5723 with the L5727-L5732 additive loop, both
        # feeding the L5748 boundary snapshot, INTER2 and the final segment.
        slope_planes=upstream.fields(scene,land)
        terrain,highest,lapse,temperature=fradj.fields(scene)
        (_,_,minimum,distance_max,distance_min,heat)=slope_planes
        upstream_in=folder/"upstream.original.inp"
        upstream_out=folder/"upstream.original"
        upstream.write_case(upstream_in,ZFACE1_M,DZ,terrain,highest,lapse,
                            temperature,minimum,distance_max,distance_min,
                            heat,land,u,v,TERRAD_KM,True)
        run([original_upstream,upstream_in,upstream_out])
        combined_u,combined_v=upstream.read_output(upstream_out)
        upstream_inp=folder/"bridge.upstream.in"
        write_bridge(upstream_inp,scene,land,weights,station_u,station_v,
                     froude=True,slope=True,terset=True)
        cpp_prepared_upstream=folder/"prepared.upstream.cpp.csv"
        cpp_final_upstream=folder/"final.upstream.cpp.csv"
        cpp_bc_upstream=folder/"boundary.upstream.cpp"
        run([args.cpp,upstream_inp,folder/"wind1.upstream.cpp",
             folder/"blend.upstream.cpp.csv",cpp_final_upstream,
             cpp_bc_upstream,cpp_prepared_upstream,
             folder/"w_faces.disabled.csv"])
        comparison_upstream_step=upstream.compare(
            upstream_out,cpp_prepared_upstream,step_u,step_v)
        u_observed,u_bc_u,u_bc_v,u_segment,u_bounds,_=original_tail(
            folder,".upstream",combined_u,combined_v)
        comparison_upstream=diag.compare(u_segment,cpp_final_upstream,
                                         u_bounds,cpp_bc_upstream)
        comparison_upstream["envelope_source"]="original TERSET L5228 in-chain (TERRAD=%g km)"%TERRAD_KM
        comparison_upstream["original_upstream_changed_components"]=(
            comparison_upstream_step["original_changed_step_one_components"])
        comparison_upstream["upstream_step_max_abs_errors"]=(
            comparison_upstream_step["max_abs_errors"])
        comparison_upstream_blend=compare_blend(
            u_observed["u"],u_observed["v"],folder/"blend.upstream.cpp.csv")
        # Original IKINE=1 pre-blend kinematic route (completeness branch; the
        # real deck has IKINE=0): literal W zeroing L5615-L5616, literal TOPOF2
        # L5621-L5622 and the literal pre-blend MINIM call L5628-L5629 using
        # the literal L5598-L5600 WINDBC snapshot, all before FRADJ/SLOPE.
        terrain,highest,lapse,temperature=fradj.fields(scene)
        kinematic_in=folder/"kinematic.original.inp"
        kinematic_uv=folder/"kinematic.original"
        kinematic_w=folder/"kinematic.original.w"
        kinematic.write_case(kinematic_in,ZFACE1_M,DZ,terrain,lapse,
                             temperature,ALPHA,KINEMATIC_NITER,
                             KINEMATIC_DIVLIM,u,v)
        run([original_kinematic,kinematic_in,kinematic_uv,kinematic_w])
        k_rows=kinematic.read_uv(kinematic_uv)
        kinematic_u=[float(row[3]) for row in k_rows]
        kinematic_v=[float(row[4]) for row in k_rows]
        k_inp=folder/"bridge.kinematic.in"
        write_bridge(k_inp,scene,land,weights,station_u,station_v,kin=True)
        cpp_prepared_kinematic=folder/"prepared.kinematic.cpp.csv"
        cpp_final_kinematic=folder/"final.kinematic.cpp.csv"
        cpp_bc_kinematic=folder/"boundary.kinematic.cpp"
        cpp_w_kinematic=folder/"w_faces.kinematic.csv"
        run([args.cpp,k_inp,folder/"wind1.kinematic.cpp",
             folder/"blend.kinematic.cpp.csv",cpp_final_kinematic,
             cpp_bc_kinematic,cpp_prepared_kinematic,cpp_w_kinematic])
        comparison_kinematic_w=kinematic.compare_w(kinematic_w,cpp_w_kinematic)
        comparison_kinematic_uv=kinematic.compare_uv(kinematic_uv,
                                                    cpp_prepared_kinematic)
        k_observed,k_bc_u,k_bc_v,k_segment,k_bounds,_=original_tail(
            folder,".kinematic",kinematic_u,kinematic_v)
        comparison_kinematic=diag.compare(k_segment,cpp_final_kinematic,
                                          k_bounds,cpp_bc_kinematic)
        comparison_kinematic["original_topof2_max_abs_error_mps"]=(
            comparison_kinematic_w["max_abs_error_mps"])
        comparison_kinematic["original_topof2_nonzero_faces"]=(
            comparison_kinematic_w["nonzero_original_faces"])
        comparison_kinematic_blend=compare_blend(
            k_observed["u"],k_observed["v"],folder/"blend.kinematic.cpp.csv")
        results[name]=dict(first_guess=comparison_first,
                           inter2=comparison_blend,final=comparison_final,
                           obrien=comparison_obrien,
                           froude=dict(step_one=comparison_froude_step,
                                       inter2=comparison_froude_blend,
                                       final=comparison_froude,
                                       boundary_input_west_east=f_bc_u[0],
                                       boundary_input_south_north=f_bc_v[0]),
                           upstream=dict(step_one=comparison_upstream_step,
                                         inter2=comparison_upstream_blend,
                                         final=comparison_upstream),
                           kinematic=dict(topof2_w=comparison_kinematic_w,
                                          step_one=comparison_kinematic_uv,
                                          inter2=comparison_kinematic_blend,
                                          final=comparison_kinematic))

    froude_adjusted=sum(r["froude"]["final"]
                        ["original_froude_adjusted_components"]
                        for r in results.values())
    upstream_changed=sum(r["upstream"]["final"]
                         ["original_upstream_changed_components"]
                         for r in results.values())
    complete=(len(results)==len(selected) and
        all(
          r["first_guess"]["status"]=="PASS" and
          r["inter2"]["status"]=="PASS" and
          r["final"]["status"]=="PASS" and
          r["obrien"]["status"]=="PASS" and
          r["obrien"]["original_iobr1_top_face_nonzero_cells"]==0 and
          r["obrien"]["original_iobr0_top_face_nonzero_cells"]>0 and
          r["froude"]["step_one"]["status"]=="PASS" and
          r["froude"]["inter2"]["status"]=="PASS" and
          r["froude"]["final"]["status"]=="PASS" and
          r["upstream"]["step_one"]["status"]=="PASS" and
          r["upstream"]["inter2"]["status"]=="PASS" and
          r["upstream"]["final"]["status"]=="PASS" and
          r["kinematic"]["topof2_w"]["status"]=="PASS" and
          r["kinematic"]["topof2_w"]["nonzero_original_faces"]>0 and
          r["kinematic"]["step_one"]["status"]=="PASS" and
          r["kinematic"]["inter2"]["status"]=="PASS" and
          r["kinematic"]["final"]["status"]=="PASS"
          for r in results.values()) and froude_adjusted>0 and
        upstream_changed>0)
    counters=dict(
        firstguess_components=sum(r["first_guess"]["components_compared"]
                                  for r in results.values()),
        blended_components=sum(r["inter2"]["components_compared"]
                               for r in results.values()),
        final_uv_div_w_components=sum(r["final"]["uv_div_w_comparisons"]
                                      for r in results.values()),
        boundary_components=sum(r["final"]["boundary_comparisons"]
                                for r in results.values()),
        obrien_uv_div_w_components=sum(r["obrien"]["uv_div_w_comparisons"]
                                       for r in results.values()),
        obrien_boundary_components=sum(r["obrien"]["boundary_comparisons"]
                                       for r in results.values()),
        obrien_cancelled_top_faces=NC*len(results),
        froude_step_one_components=sum(r["froude"]["step_one"]
                                       ["compared_components"]
                                       for r in results.values()),
        froude_final_uv_div_w_components=sum(r["froude"]["final"]
                                             ["uv_div_w_comparisons"]
                                             for r in results.values()),
        froude_boundary_components=sum(r["froude"]["final"]
                                       ["boundary_comparisons"]
                                       for r in results.values()),
        froude_adjusted_step_one_components=froude_adjusted,
        upstream_step_one_components=sum(r["upstream"]["step_one"]
                                         ["compared_components"]
                                         for r in results.values()),
        upstream_final_uv_div_w_components=sum(r["upstream"]["final"]
                                               ["uv_div_w_comparisons"]
                                               for r in results.values()),
        upstream_boundary_components=sum(r["upstream"]["final"]
                                         ["boundary_comparisons"]
                                         for r in results.values()),
        upstream_changed_step_one_components=upstream_changed,
        kinematic_topof2_w_faces=sum(r["kinematic"]["topof2_w"]
                                     ["compared_faces"]
                                     for r in results.values()),
        kinematic_step_one_components=sum(r["kinematic"]["step_one"]
                                          ["components"]
                                          for r in results.values()),
        kinematic_final_uv_div_w_components=sum(r["kinematic"]["final"]
                                                ["uv_div_w_comparisons"]
                                                for r in results.values()),
        kinematic_boundary_components=sum(r["kinematic"]["final"]
                                          ["boundary_comparisons"]
                                          for r in results.values())
    )
    report=dict(
        status="PASS_D9A_SELECTED_CHAINED_ORIGINAL_SOURCES" if complete else "FAIL",
        scope="synthetic identity upstream WIND1 original -> original INTER2 U/V -> original SMOOTH/DIVCEL/W, replayed with and without the original IOBR=1 O'Brien/MINIM tail, with the original IKINE=1 pre-blend TOPOF2+MINIM kinematic route, with the original IFRADJ=1 Froude terrain adjustment, and with the original IFRADJ=1+ISLOPE=1 upstream sequence of the real case deck; no HEATFX/ELUSTR/STHEOR/ADJUST, not real 2022 full DIAGNO",
        vendor_blob=sha,original_reference=meta,
        obrien_controls=dict(cellzb_origin_m=ZFACE1_M,minim_iterations=MINIM_ITERATIONS,
                             minim_divergence_limit_per_s=MINIM_DIVLIM,iobr=1),
        froude_controls=dict(iradj=1,isurft=fradj.ISURFT,tinf_k=fradj.TINF_K,
                             critfn=fradj.CRITFN,cellzb_origin_m=ZFACE1_M,
                             envelope_margin_m=fradj.ENVELOPE_MARGIN_M,
                             slope_and_heat_stages_enabled=False),
        kinematic_controls=dict(ikine=1,alpha=ALPHA,niter=KINEMATIC_NITER,
                                divlim_per_s=KINEMATIC_DIVLIM,
                                cellzb_origin_m=ZFACE1_M,
                                real_case_path=False,
                                divlim_note="deterministic iteration count; the deck's DIVLIM=5e-6 makes the original convergence test threshold-sensitive, measured calm-scene spread 2.8e-03 m/s"),
        upstream_controls=dict(iwf_cod=1,ifradj=1,islope=1,ikine=0,iobr=0,
                               terset_envelope="original L5228 in-chain",
                               terrad_km=TERRAD_KM,
                               isurft=upstream.chain_fradj.ISURFT,
                               tinf_k=upstream.chain_fradj.TINF_K,
                               critfn=upstream.chain_fradj.CRITFN,
                               cellzb_origin_m=ZFACE1_M,
                               envelope_margin_m=upstream.chain_fradj.ENVELOPE_MARGIN_M,
                               water_class_range=[upstream.WATER_FIRST,
                                                  upstream.WATER_LAST]),
        tolerance_wind_mps=COMP_TOL,summary=counters,scenes=results)
    (args.out/"p6d9a-original-chained-source-parity.json").write_text(
        json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    if not complete:raise SystemExit(1)

if __name__=="__main__":
    main()
