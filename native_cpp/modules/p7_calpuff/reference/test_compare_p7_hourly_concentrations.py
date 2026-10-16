#!/usr/bin/env python3
"""Self-contained negative and positive tests for the C1/C2 float32 comparator."""
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

SCRIPT=Path(__file__).with_name("compare_p7_hourly_concentrations.py")
spec=importlib.util.spec_from_file_location("p7fields",SCRIPT)
p7=importlib.util.module_from_spec(spec)
spec.loader.exec_module(p7)

def frame(value:bytes) -> bytes:
    n=struct.pack("<i",len(value))
    return n+value+n

def example(path:Path,frames:list[list[float]],name:str="H-3",wrong_trailer=False)->None:
    data=frame(b"CONC.DAT".ljust(96,b" "))
    data+=frame(struct.pack("<i",1))
    data+=frame(b"Original or native metadata".ljust(132,b" "))
    for h,values in enumerate(frames):
        data+=frame(struct.pack("<8i",2022,1,h,0,2022,1,h+1,0))
        data+=frame(struct.pack("<ii16sff",0,1,b"TOTAL           ",0.,0.))
        data+=frame(name.encode().ljust(8,b" ")+b"      1"+struct.pack("<4f",*values))
    if wrong_trailer:
        data=data[:-4]+struct.pack("<i",123)
    path.write_bytes(data)

class TestIndependentFields(unittest.TestCase):
    def test_metadata_changes_do_not_change_h3_equality(self):
        with tempfile.TemporaryDirectory() as d:
            a,b=Path(d)/"a.con",Path(d)/"b.con"
            example(a,[[1,0,2,3],[2,4,0,0]])
            example(b,[[1,0,2,3],[2,4,0,0]])
            b.write_bytes(frame(b"extra provenance")+b.read_bytes())
            aa=p7.read_fields(a,2,2,2)
            bb=p7.read_fields(b,2,2,2)
            c=p7.compare(aa,bb,2,2)
            self.assertNotEqual(aa["sha256"],bb["sha256"])
            self.assertTrue(c["bitwise_identical"])
            self.assertEqual(c["matching_real4"],8)

    def test_reports_first_hour_and_receptor_without_hiding_small_delta(self):
        with tempfile.TemporaryDirectory() as d:
            a,b=Path(d)/"a.con",Path(d)/"b.con"
            example(a,[[1,2,3,4],[1,2,3,4]])
            example(b,[[1,2,3,4],[1,2,4,4]])
            result=p7.compare(p7.read_fields(a,2,2,2),p7.read_fields(b,2,2,2),2,2)
            self.assertFalse(result["bitwise_identical"])
            self.assertEqual(result["matching_real4"],7)
            self.assertEqual(result["first_difference"]["hour_1based"],2)
            self.assertEqual(result["first_difference"]["i_1based"],1)
            self.assertEqual(result["first_difference"]["j_1based"],2)

    def test_reject_truncation_and_wrong_hour_count(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"c.con"
            example(path,[[1,2,3,4]],wrong_trailer=True)
            with self.assertRaises(ValueError):p7.read_fields(path,2,2,1)
            example(path,[[1,2,3,4]])
            with self.assertRaises(ValueError):p7.read_fields(path,2,2,2)

    def test_reject_all_zero_and_nan(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"d.con"
            example(path,[[0,0,0,0]])
            with self.assertRaises(ValueError):p7.read_fields(path,2,2,1)
            example(path,[[1,float("nan"),2,3]])
            with self.assertRaises(ValueError):p7.read_fields(path,2,2,1)

if __name__=="__main__":
    unittest.main()
