#!/usr/bin/env python3
"""Audit frozen original CALPUFF WROUT1/PG-AVET output, not fake parity.

For the frozen 2022 143-hour MWET=0 deck, PG AVET equals PGTIME (60min);
PG sigma-y adjustment is 1. That does NOT remove the need to reproduce the
143 hourly receptor accumulation and the WROUT1 headers/record order.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import struct
import sys
from pathlib import Path

P7_FROZEN_CON_SHA = "0d51bdb68ff1a5798048bc41067107d3ffe10dc6222f25336df856bcbf48ba10"
ORIGINAL_RECORDS = 3655
DATA_RECORDS = 143*3
NONDATA_RECORDS = ORIGINAL_RECORDS-DATA_RECORDS


def one(deck: str, key: str) -> float:
    matches=re.findall(r"!\s*"+re.escape(key)+r"\s*=\s*([^!\n\r]+)!",deck,re.I)
    if len(matches)!=1:
        raise ValueError(f"control {key}: active value count={len(matches)}")
    return float(matches[0].strip().replace("D","E").replace("d","e"))


def audit(control: Path, original: Path, report: Path | None,
          original_met: Path | None = None) -> dict:
    deck=control.read_text(encoding="latin-1")
    if int(one(deck,"MWET"))!=0 or int(one(deck,"METFM"))!=1:
        raise ValueError("selected dry original 2022 output only")
    avet=one(deck,"AVET")
    pgtime=one(deck,"PGTIME")
    if (avet,pgtime)!=(60.0,60.0):
        raise ValueError("PG averaging case-specific branch changed")
    factor=(avet/pgtime)**0.2
    if factor!=1.0:
        raise AssertionError("AVET is not neutral as presumed")
    data=original.read_bytes()
    if hashlib.sha256(data).hexdigest()!=P7_FROZEN_CON_SHA:
        raise AssertionError("frozen original puff.con SHA256 drift")
    hist=collections.Counter()
    entries=[]
    record_layout=[]
    pos=0
    while pos<len(data):
        if pos+8>len(data):
            raise ValueError("truncated original Fortran sequential record marker")
        size=struct.unpack_from("<i",data,pos)[0]
        if size<0 or size>len(data)-pos-8:
            raise ValueError(f"invalid original record length {size} at {pos}")
        end=pos+4+size
        suffix=struct.unpack_from("<i",data,end)[0]
        if suffix!=size:
            raise ValueError(f"Fortran framing mismatch at {pos}: {size}/{suffix}")
        hist[size]+=1
        record_layout.append((pos,size))
        if len(entries)<12:
            entries.append({"ordinal":len(entries)+1,"byte_offset":pos,
                            "payload_bytes":size,
                            "first_16_hex":data[pos+4:pos+4+min(size,16)].hex()})
        pos=end+4
    if pos!=len(data) or sum(hist.values())!=ORIGINAL_RECORDS:
        raise AssertionError("frozen original Fortran record count changed")
    # The previous ledger inferred all 3,226 non-hourly records were WROUT1
    # missing functions. Distinguish the actual embedded control/comment
    # prefix from the *remaining* standalone metadata before accepting that
    # implementation estimate. Never copy any frozen payload into native output.
    if record_layout[0][1]!=96 or record_layout[1][1]!=4:
        raise AssertionError("vendor CONC.DAT version/comment-count header changed")
    first_start=record_layout[0][0]+4
    version=data[first_start:first_start+96]
    if not version.startswith(b"CONC.DAT"):
        raise AssertionError("frozen first record is not CONC.DAT")
    comments_at=record_layout[1][0]+4
    ncomments=struct.unpack_from("<i",data,comments_at)[0]
    if not 0<=ncomments<=len(record_layout)-2:
        raise AssertionError("invalid original embedded comment count")
    comment_records=record_layout[2:2+ncomments]
    comments_hist=collections.Counter(n for _,n in comment_records)
    trailing_nondata=NONDATA_RECORDS-2-ncomments
    if trailing_nondata<0:
        raise AssertionError("comment records exceed original non-DATA budget")
    # Infer the original echo's INPUT origins before porting the WROUT1
    # comment writer. Copying bytes from frozen puff.con is forbidden.
    echo=[data[p+4:p+4+n].decode("latin-1").rstrip()
          for p,n in comment_records]
    deck_lines=[line.rstrip() for line in
                control.read_text(encoding="latin-1").splitlines()]
    deck_set=set(deck_lines)
    direct_matches=sum(line in deck_set for line in echo[2:])
    from difflib import SequenceMatcher
    matcher=SequenceMatcher(None,deck_lines,echo[2:],autojunk=True)
    spans=matcher.get_matching_blocks()
    longests=sorted((size,i,j) for i,j,size in spans if size>0)[-6:]
    echo_diagnostics={
        "deck_lines":len(deck_lines),
        "echo_records":len(echo),
        "echo_first_lines":echo[:10],
        "echo_last_lines":echo[-10:],
        "echo_lines_equal_to_deck_line":direct_matches,
        "direct_sequence_ratio":round(matcher.ratio(),6),
        "longest_exact_runs":[
            {"count":size,"deck_index":i,"echo_after_preamble_index":j}
            for size,i,j in longests],
    }
    print("P7_WROUT1_ECHO_INPUT_PROVENANCE="+json.dumps(
        echo_diagnostics,ensure_ascii=True))
    if original_met:
        met_bytes=original_met.read_bytes()
        expected_met="b1823cda92280888d70b00961ab39486036a3086e18637fff21efb4f4b237d30"
        if hashlib.sha256(met_bytes).hexdigest()!=expected_met:
            raise AssertionError("frozen MET.DAT SHA256 drift")
        met_echo=[]
        offset=0
        met_record_count=0
        # Source header is a sequence of Fortran unformatted records; avoid
        # scanning hourly wind arrays by limiting to the first 8 MB.
        while offset+8<=len(met_bytes) and offset<8_000_000:
            size=struct.unpack_from("<i",met_bytes,offset)[0]
            if size<0 or offset+size+8>len(met_bytes):
                raise ValueError("MET.DAT record marker mismatch")
            if struct.unpack_from("<i",met_bytes,offset+4+size)[0]!=size:
                raise ValueError("MET.DAT record trailer mismatch")
            if size==132:
                met_echo.append(met_bytes[offset+4:offset+4+size]
                                .decode("latin-1").rstrip())
            offset+=size+8
            met_record_count+=1
        extra=echo[2+len(deck_lines):]
        if len(extra)!=1118:
            raise AssertionError("original CALPUFF control vs MET suffix changed")
        in_met=sum(line in set(met_echo) for line in extra)
        sseq=SequenceMatcher(None,met_echo,extra,autojunk=True)
        blocks=sseq.get_matching_blocks()
        longest=max(blocks,key=lambda item:item.size)
        match={
            "met_header_record_count_scanned":met_record_count,
            "met_132_byte_records":len(met_echo),
            "post_puff_control_extra_lines":len(extra),
            "extra_lines_equal_to_met_comment":in_met,
            "met_echo_sequence_ratio":round(sseq.ratio(),6),
            "longest_met_match":{
                "length":longest.size,
                "met_comment_index":longest.a,
                "puff_con_extra_index":longest.b},
            "met_first_132_lines":met_echo[:5],
            "extra_first_lines":extra[:8]
        }
        echo_diagnostics["met_header_echo_provenance"]=match
        print("P7_WROUT1_CALMET_COMMENT_MATCH="+
              json.dumps(match,ensure_ascii=True))
    comment_examples=[]
    for pos_comment,size_comment in comment_records[:5]:
        raw=data[pos_comment+4:pos_comment+4+size_comment]
        comment_examples.append(raw[:112].decode("latin-1").rstrip())
    tail=record_layout[2+ncomments:]
    first_tail=[{"ordinal":2+ncomments+i+1,"bytes":n,
                 "ascii_prefix":data[p+4:p+4+min(n,32)].decode("latin-1",
                                                             errors="replace")}
                for i,(p,n) in enumerate(tail[:12])]
    # Identify the known 143 x (period, TOTAL descriptor, H-3 REAL4 field)
    # records *by layout and payload*, and enumerate every remaining record.
    # This closes the erroneous equation "non-DATA = unported headers".
    counts=collections.Counter()
    metadata=[]
    for ordinal,(p,n) in enumerate(tail,start=3+ncomments):
        body=data[p+4:p+4+n]
        record_type=None
        if n==32:
            i=struct.unpack_from("<8i",body)
            if (1900<=i[0]<=2100 and 1<=i[1]<=366 and 0<=i[2]<=23 and
                1900<=i[4]<=2100 and 1<=i[5]<=366 and 0<=i[6]<=23):
                record_type="period"
            elif body[8:24].startswith(b"TOTAL") and (
                 body[8:24].rstrip(b" ")==b"TOTAL"):
                record_type="total_source"
        if n==10015 and body[:8]==b"H-3     ":
            record_type="h3_field"
        if record_type:
            counts[record_type]+=1
        else:
            metadata.append({
                "ordinal":ordinal,
                "bytes":n,
                "hex_prefix":body[:64].hex(),
                "latin1_prefix":body[:96].decode("latin-1",
                                               errors="replace")
            })
    if counts!={"period":143,"total_source":143,"h3_field":143}:
        raise AssertionError(f"unexpected original hourly stream topology: {counts}")
    source_type_body=data[record_layout[2+ncomments+1][0]+4:
                          record_layout[2+ncomments+1][0]+4+52]
    if len(source_type_body)!=52 or struct.unpack("<13i",source_type_body)!=(1,)+(0,)*12:
        raise AssertionError("original 13 INTEGER*4 source category counts changed")
    if len(metadata)!=trailing_nondata:
        raise AssertionError("WROUT1 residual metadata count inconsistent")
    for item in metadata:
        print("P7_ORIGINAL_WROUT1_METADATA"
              f" ORDINAL={item['ordinal']} BYTES={item['bytes']}"
              f" HEX={item['hex_prefix']}"
              f" TEXT={item['latin1_prefix']!r}")
    numeric_header_pos,numeric_header_size=record_layout[2+ncomments]
    if numeric_header_size!=300:
        raise AssertionError("unexpected numeric WROUT1 general metadata record size")
    header=data[numeric_header_pos+4:numeric_header_pos+304]
    print("P7_VENDOR_WROUT1_300B_HEX="+header.hex())
    print("P7_ORIGINAL_WROUT1_PREFIX_DIAG"
          f" EMBEDDED_CONTROL_COMMENTS={ncomments}"
          f" COMMENTS_RECORD_BYTES={dict(sorted(comments_hist.items()))}"
          f" NONDATA_AFTER_COMMENT_PREFIX={trailing_nondata}"
          f" FIRST_POSTPREFIX_RECORD={2+ncomments+1}")
    out={
        "status":"ORIGINAL_WROUT1_OUTPUT_REFERENCE_AUDITED",
        "control_scope":"Hefei 2022 METFM=1 MWET=0 143h",
        "original_con_sha256":P7_FROZEN_CON_SHA,
        "original_con_bytes":len(data),
        "original_sequential_records":ORIGINAL_RECORDS,
        "original_143_hour_data_records_from_p7g_structure_parity":DATA_RECORDS,
        "original_nondata_records":NONDATA_RECORDS,
        "current_cpp_minimal_writer_nondata_records":2,
        "prior_ledger_unclassified_nondata_records":NONDATA_RECORDS-2,
        "missing_vendor_WROUT1_nondata_records":"REQUIRES_TYPE_CLASSIFICATION",
        "original_record_lengths":{str(k):v for k,v in sorted(hist.items())},
        "original_first_records":entries,
        "version_record_ascii":version.decode("latin-1").rstrip(),
        "embedded_comment_count":ncomments,
        "embedded_comment_record_byte_sizes":dict(sorted(comments_hist.items())),
        "embedded_comment_first_lines":comment_examples,
        "echo_input_provenance":echo_diagnostics,
        "remaining_nondata_records_after_embedded_comments":trailing_nondata,
        "first_records_after_embedded_comments":first_tail,
        "independently_classified_data_record_counts":dict(counts),
        "post_comment_extra_metadata_records":metadata,
        "avet_minutes":avet,"pgtime_minutes":pgtime,
        "original_PG_sigma_y_averaging_factor":factor,
        "avenue":"WROUT1 header records and whole-case concentration/period writer must be ported; AVET=PGTIME does not waive them",
        "native_header_numerical_parity":"NOT_YET_IMPLEMENTED",
        "native_143h_concentration_parity":"NOT_YET_IMPLEMENTED",
    }
    if report:
        report.parent.mkdir(parents=True,exist_ok=True)
        report.write_text(json.dumps(out,indent=2)+"\n")
    print("P7_ORIGINAL_WROUT1_AUDIT=PASS "
          f"RECORDS={ORIGINAL_RECORDS} DATA={DATA_RECORDS} "
          f"NONDATA={NONDATA_RECORDS} ECHO={ncomments} METADATA=6")
    print("P7_ORIGINAL_PG_AVET=PASS AVET=60 PGTIME=60 AVERAGING_FACTOR=1")
    print("P7_CPP_WROUT1_143H_CONCENTRATION=NOT_YET_IMPLEMENTED")
    return out


def source_wrou1_writes(vendor: Path) -> None:
    # Inspect original source independently of the frozen binary. This
    # identifies each 300/52/240/15/16/20 record's authoring statements.
    source=vendor.read_text(encoding="latin-1").splitlines()
    begin=next((i for i,s in enumerate(source) if re.match(
        r"^\s{5,}SUBROUTINE\s+WROUT1\b",s,re.I)),None)
    if begin is None:
        raise ValueError("vendor WROUT1 subroutine not found")
    stop=next((i for i in range(begin+1,len(source))
               if re.match(r"^\s{5,}END\s*(?:!.*)?$",source[i],re.I)),None)
    if stop is None:
        raise ValueError("vendor WROUT1 routine boundary missing")
    # Vendor source is the evidence, not a retyped assumption about the record.
    matches=[(i+1,source[i].strip()) for i in range(begin,stop)
             if re.search(r"\bWRITE\s*\(|\bFORMAT\s*\(|\bREWIND\b|"
                          r"\bNCOM\w*\b|\bCREC\w*\b",source[i],re.I)]
    print(f"P7_VENDOR_WROUT1_SOURCE BEGIN={begin+1} END={stop+1}"
          f" WRITE_ANCHORS={len(matches)}")
    for index,line in matches[:65]:
        print(f"P7_VENDOR_WROUT1_STATEMENT LINE={index} CODE={line[:160]!r}")
    # Keep original fixed-form continuation lines to preserve the exact
    # ordered payload fields of 300-byte and 52-byte header records.
    for line_number in range(57174,57235):
        print(f"P7_VENDOR_WROUT1_RAW LINE={line_number}"
              f" CODE={source[line_number-1][:126]!r}")
    # Print declarations visible in the original WROUT1 routine; names
    # matter for mixed REAL4/INTEGER4/CHARACTER header serialization.
    for line_number in range(56770,57126):
        raw=source[line_number-1]
        if re.search(r"^      (?:include|character|integer|real|logical|double|data)\b",raw,re.I):
            print(f"P7_VENDOR_WROUT1_DECL LINE={line_number}"
                  f" CODE={raw[:126]!r}")


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--control",type=Path,required=True)
    p.add_argument("--original-con",type=Path,required=True)
    p.add_argument("--vendor",type=Path)
    p.add_argument("--original-met",type=Path)
    p.add_argument("--report",type=Path)
    args=p.parse_args()
    try:
        audit(args.control,args.original_con,args.report,args.original_met)
        if args.vendor is not None:
            source_wrou1_writes(args.vendor)
        return 0
    except (OSError,ValueError,AssertionError,struct.error) as e:
        print("P7_ORIGINAL_WROUT1_AUDIT=FAIL "+str(e),file=sys.stderr)
        return 1

if __name__=="__main__":
    raise SystemExit(main())
