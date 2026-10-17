"""Strict numerical parity checker for original Fortran READ62 IFMT=1 and C++ P4 UP.DAT.

Compares 6201 snapshot header, original/retained level counts and all five level fields.
Checks actual output quantization (pressure 0.1 hPa, height 1 m, T 0.1 K,
wind direction 1 degree, wind speed 1 m/s). Does not infer success from process exit.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path

GROUP = re.compile(r"\s*(-?\d+\.\d+)/\s*(-?\d+\.)/\s*(-?\d+\.\d+)/\s*(-?\d+)/\s*(-?\d+)")
COLUMNS = ("pressure_hpa", "height_m", "temperature_k", "wd_deg", "ws_mps")


def parse_updat(path: Path):
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) < 8 or "UP.DAT" not in lines[0] or lines[3].strip() != "NONE":
        raise ValueError(f"invalid IFMT1 UP.DAT header: {path}")
    records = {}
    current = None
    for line in lines[7:]:
        if line.startswith("   6201"):
            p = line.split()
            if len(p) != 14:
                raise ValueError(f"bad 6201 header fields ({len(p)}): {line!r}")
            if p[2:7] != p[7:12]:
                raise ValueError("snapshot begin/end mismatch")
            key = tuple(int(i) for i in p[2:7])
            if key in records:
                raise ValueError(f"duplicate UP.DAT time {key}")
            records[key] = {"station": p[1], "mlev": int(p[12]),
                            "istop": int(p[13]), "levels": [], "qa": []}
            current = records[key]
        elif "->->->" in line:
            if current is None: raise ValueError("orphan diagnostic")
            current["qa"].append(line.strip())
        elif line.strip():
            if current is None: raise ValueError(f"unexpected preamble: {line!r}")
            entries = GROUP.findall(line)
            if not entries:
                raise ValueError(f"unsupported numeric record: {line!r}")
            current["levels"] += [tuple(float(x) for x in vals) for vals in entries]
    for ts, rec in records.items():
        if len(rec["levels"]) != rec["istop"]:
            raise ValueError(f"UP.DAT level count invalid {ts}: {rec['istop']} vs {len(rec['levels'])}")
    return records


def compare(reference: Path, candidate: Path):
    ref, cpp = parse_updat(reference), parse_updat(candidate)
    result = {"reference": str(reference), "candidate": str(candidate),
              "reference_profiles": len(ref), "candidate_profiles": len(cpp),
              "matched_profiles": 0, "matched_levels": 0, "matched_fields": 0,
              "differences": [], "max_abs_error": {key: 0.0 for key in COLUMNS}}
    if set(ref) != set(cpp):
        result["differences"].append({
            "kind": "time_membership",
            "missing": sorted(set(ref) - set(cpp))[:20],
            "extra": sorted(set(cpp) - set(ref))[:20]})
    for stamp in sorted(set(ref) & set(cpp)):
        a, b = ref[stamp], cpp[stamp]
        result["matched_profiles"] += 1
        for field in ("station", "mlev", "istop", "qa"):
            if a[field] != b[field]:
                result["differences"].append({
                    "time": stamp, "kind": field, "reference": a[field], "candidate": b[field]})
        for i, (x, y) in enumerate(zip(a["levels"], b["levels"])):
            result["matched_levels"] += 1
            for k, f in enumerate(COLUMNS):
                delta = abs(x[k] - y[k])
                result["max_abs_error"][f] = max(result["max_abs_error"][f], delta)
                if delta > 1.0e-6:
                    if len(result["differences"]) < 100:
                        result["differences"].append({
                            "time": stamp, "level": i, "kind": f,
                            "reference": x[k], "candidate": y[k], "abs_error": delta})
                else:
                    result["matched_fields"] += 1
    result["pass"] = (
        result["reference_profiles"] > 0 and
        result["reference_profiles"] == result["candidate_profiles"] and
        len(result["differences"]) == 0)
    return result


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--reference", type=Path, required=True)
    ap.add_argument("--candidate", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    args=ap.parse_args()
    report=compare(args.reference,args.candidate)
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False)+"\n")
    print("P4_NUMERICAL_PARITY",json.dumps(
        {k:v for k,v in report.items() if k in ("pass","reference_profiles","candidate_profiles",
        "matched_profiles","matched_levels","matched_fields","max_abs_error")}))
    if not report["pass"]:
        print("First differences:",json.dumps(report["differences"][:5]))
        raise SystemExit(1)


if __name__=="__main__":
    main()
