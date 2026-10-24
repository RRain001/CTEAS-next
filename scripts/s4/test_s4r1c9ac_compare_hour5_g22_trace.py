"""Validation tests for the scoped hour-five comparison format."""
import struct
import unittest
from scripts.s4.s4r1c9ac_compare_hour5_g22_trace import NC, NZ, STAGE_ARRAYS, compare, extract
from scripts.s4.s4r1c9n_compare_hour3_g22_trace import compare_words, frozen_limit

def fixture(hour=6):
    result=bytearray()
    for stage,names in STAGE_ARRAYS.items():
        result += struct.pack("<5i",hour,82,85,9,stage)
        result += bytes(NC*(NZ if stage==50 else 1)*len(names)*4)
    return bytes(result)

class HourFiveFormatTests(unittest.TestCase):
    def test_expected_hour(self):
        self.assertEqual(list(extract(fixture(),(6,))[6]),[10,20,30,40,50])
    def test_wrong_hour(self):
        with self.assertRaisesRegex(ValueError,"wrong hour"):
            extract(fixture(5),(6,))
    def test_truncation(self):
        with self.assertRaisesRegex(ValueError,"truncated"):
            extract(fixture()[:-4],(6,))
    def test_extra_bytes(self):
        with self.assertRaisesRegex(ValueError,"trailing"):
            extract(fixture()+b"x",(6,))
    def test_identical(self):
        data=extract(fixture(),(6,))[6]
        result=compare(data,data,set(range(63)))
        self.assertEqual((result["compared_real4"],result["bitwise_equal"]),(181220,181220))
    def test_water_ustar_bitwise_gate(self):
        a=extract(fixture(),(6,))[6]
        b=dict(a)
        field=bytearray(b[40])
        struct.pack_into("<I",field,4,1)
        b[40]=bytes(field)
        self.assertEqual(compare(a,b,set(range(63)))["status"],"FAIL_FROZEN_G22_INTERMEDIATES")
    def test_temperature_limit(self):
        a=bytes(NC*4); b=bytearray(a)
        struct.pack_into("<f",b,0,0.1)
        self.assertEqual(compare_words(a,b,1,0,{0},"temp2d")["frozen_tolerance_exceedances"],1)
        self.assertEqual(frozen_limit("temp2d",300),0.001)

if __name__=="__main__":
    unittest.main()
