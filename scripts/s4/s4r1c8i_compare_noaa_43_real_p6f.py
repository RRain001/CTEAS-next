#!/usr/bin/env python3
"""Independent 43 REAL4 P6F field audit on untouched original MET.DAT.

Native C++ executable takes only genuine NOAA P1-P5 forcing, never original
MET.DAT. This parser is an independent later forensic comparator, not a
source of physical values for the native candidate. It asserts original
six-hour 45-field layout, clock, GEO and original station cardinalities.
"""
from __future__ import annotations
import argparse,hashlib,json,math,struct
from pathlib import Path
NX,NY,NZ,NC=82,85,9,82*85
F32=struct.Struct("<"+str(NC)+"f")
INT=struct.Struct("<"+str(NC)+"i")
LABELS=(
    [s+"  "+str(k) for k in range(1,10)
     for s in ("U-LEV","V-LEV","WFACE")]
    +["T-LEV  "+str(k) for k in range(1,10)]
    +["IPGT    ","USTAR   ","ZI      ","EL      ","WSTAR   ",
      "TEMPK   ","RHO     ","QSW     ","IRH     "]
)
REAL_LABELS=[x for x in LABELS if x not in ("IPGT    ","IRH     ")]
assert len(LABELS)==45 and len(REAL_LABELS)==43
def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
def fortran_records(data:bytes):
    out=[];at=0
    while at<len(data):
        if at+8>len(data):raise ValueError("original MET truncated marker")
        size,=struct.unpack_from("<i",data,at)
        if size<0 or at+size+8>len(data):
            raise ValueError("original MET invalid Fortran record size")
        payload=data[at+4:at+4+size]
        tail,=struct.unpack_from("<i",data,at+4+size)
        if size!=tail:raise ValueError("original MET record trailer changed")
        out.append(payload);at+=size+8
    return out
def original_hour(path:Path):
    records=fortran_records(path.read_bytes())
    if len(records)<10 or len(records[0])!=96 or
        records[0][:16].decode("ascii").strip()!="CALMET.DAT":
        raise ValueError("G57 must parse real CALMET.DAT 2.1 output")
    if len(records[1])!=4:raise ValueError("G57 original NCOM missing")
    comments,=struct.unpack("<i",records[1])
    if comments<0 or comments>10000:
        raise ValueError("G57 original comment count invalid")
    header=records[comments+2]
    if len(header)!=176:
        raise ValueError("G57 original OUTHD controls missing")
    irlg,irtype,nx,ny,nz=struct.unpack_from("<5i",header,48)
    iwfcod,nss,nus,nps=struct.unpack_from("<4i",header,80)
    if (irlg,irtype,nx,ny,nz,iwfcod,nss,nus,nps)!=
       (6,1,NX,NY,NZ,1,2,1,0):
        raise ValueError("G57 source model sixhour 2SS1US identity changed")
    hourly=[]
    for payload in records[comments+3:]:
        if len(payload)<24:raise ValueError("G57 original record too short")
        label=payload[:8].decode("ascii")
        a,asec,b,bsec=struct.unpack_from("<4i",payload,8)
        if a==0 and b==0:continue
        if len(payload)!=24+4*NC:
            raise ValueError("G57 original hourly field shape wrong")
        hourly.append((label,(a,asec,b,bsec),payload[24:]))
    if len(hourly)!=6*45:raise ValueError("G57 missing original fields")
    groups=[hourly[i:i+45] for i in range(0,len(hourly),45)]
    prev=None
    for group in groups:
        if [x[0] for x in group]!=LABELS:
            raise ValueError("G57 original output field order/masks changed")
        clocks={x[1] for x in group}
        if len(clocks)!=1:raise ValueError("G57 original hour clocks disagree")
        t=next(iter(clocks))
        if t[0]!=t[2] or t[1]!=0 or t[3]!=3600:
            raise ValueError("G57 original Fortran exact hour clock changed")
        if prev is not None and t[0]!=prev+1:
            raise ValueError("G57 original source sixhour continuity failed")
        prev=t[0]
    if groups[0][0][1][0]!=202215201:
        raise ValueError("G57 original NOAA selected first hour 2022-06-01 01 UTC shifted")
    return {label:payload for label,_,payload in groups[0]},len(groups)
def native_hour(path:Path):
    raw=path.read_bytes()
    one=8+F32.size
    if len(raw)!=43*one:
        raise ValueError("G57 native 43 firsthour REAL4 byte extent changed")
    result={}
    for k,label in enumerate(REAL_LABELS):
        part=raw[k*one:(k+1)*one]
        actual=part[:8].decode("ascii")
        if actual!=label:raise ValueError("G57 native P6F output labels/order altered")
        result[label]=F32.unpack(part[8:])
    return result
def tol(label:str,a:float,b:float):
    if label.startswith(("U-LEV","V-LEV","WFACE","WSTAR","USTAR")):
        return 2e-4
    if label.startswith(("T-LEV","TEMPK")):
        return 2e-4
    if label=="ZI      ":
        return 5e-3+5e-5*max(abs(a),abs(b))
    if label=="EL      ":
        return 2048. if max(abs(a),abs(b))>1e8 else \
               2e-3+1e-4*max(abs(a),abs(b))
    if label=="RHO     ":return 2e-4
    if label=="QSW     ":return 2e-4
    raise ValueError("G57 unclassified original physical field")
def compare(original:Path,native:Path,log:Path,receipt:Path,report:Path):
    accepted=json.loads(receipt.read_text())
    if accepted.get("status")!="PASS_SOURCE_ONLY_ORIGINAL_NOAA_6H_TEMP3D" or
       accepted.get("sixhour_original_met_byte_identical") is not True or
       "S4R1C8I_REAL_NOAA_NATIVE_P6F_REAL_FIELDS=PRODUCED_UNVERIFIED" not in log.read_text() or
       "INTEGER_IPGT_IRH=NOT_ACCEPTED" not in log.read_text():
        raise ValueError("G57 requires independently accepted G56 original & native source")
    orig,hours=original_hour(original)
    real=native_hour(native)
    fields={}
    exceeding=[]
    total=0
    maxoverall=0.
    for label in REAL_LABELS:
        a=F32.unpack(orig[label]);b=real[label]
        mx=0.;s=0.;nfail=0;worst=None
        for idx,(x,y) in enumerate(zip(a,b,strict=True)):
            if not(math.isfinite(x) and math.isfinite(y)):
                raise ValueError("G57 original/native P6F nonfinite")
            delta=abs(x-y)
            if delta>mx:
                mx=delta
                worst={"i":idx%NX+1,"j":idx//NX+1,"original":x,
                       "native":y,"abs_error":delta}
            if delta>tol(label,x,y):
                nfail+=1
                if len(exceeding)<18:
                    exceeding.append({"field":label,"i":idx%NX+1,
                                      "j":idx//NX+1,"orig":x,"native":y,
                                      "abs_diff":delta})
            s+=delta
        total+=nfail;maxoverall=max(maxoverall,mx)
        fields[label.strip()]={"max_abs":mx,"mean_abs":s/NC,
                               "exceedances":nfail,"worst":worst}
    status=("PASS_SOURCE_SCOPED_REAL_NOAA_NATIVE_P6F_43_REAL_FIELDS"
            if total==0 else "FAIL_REAL_NOAA_NATIVE_P6F_REAL_FIELDS")
    result={
        "status":status,"original_full_six_hour_met_sha256":sha(original),
        "native_43real_sha256":sha(native),
        "original_hourly_fields_per_hour":45,"original_hours":hours,
        "native_scoped_firsthour_reals":len(real),"grid":[NX,NY,NZ],
        "float_compared":len(real)*NC,"above_tolerance":total,
        "max_abs_across_units_not_aggregated":maxoverall,
        "per_field":fields,"first_exceedances":exceeding,
        "original_intermediates_in_native":False,
        "IPGT_IRH_integer2":"NOT_ACCEPTED",
        "full_45field_p6f":"NOT_ACCEPTED",
        "native_sixhour_causal":"NOT_ACCEPTED","p7":"NOT_ACCEPTED",
    }
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("S4R1C8I_REAL_NOAA_NATIVE_43REAL="+status)
    print("S4R1C8I_43REAL_ABOVE_TOLERANCE="+str(total))
    print("S4R1C8I_45FIELD_G26_P7=NOT_ACCEPTED")
    return total==0
def main():
    ap=argparse.ArgumentParser()
    for k in ("original","native","log","receipt","report"):
        ap.add_argument("--"+k,type=Path,required=True)
    a=ap.parse_args()
    if not compare(a.original,a.native,a.log,a.receipt,a.report):
        raise SystemExit(3)
if __name__=="__main__":main()
