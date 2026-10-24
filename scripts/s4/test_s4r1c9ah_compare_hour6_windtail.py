"""Fourth-hour windtail comparison shape, clock and frozen tolerance tests."""
import struct
import unittest
from scripts.s4.s4r1c9ah_compare_hour6_windtail import STAGES,HOUR6_UTC_END
from scripts.s4.s4r1c9q_compare_hour3_windtail import compare,decode,COUNTS,FROZEN_WIND_ABS_TOL

def event(stage=90,hour=7):
    return struct.pack("<5i",hour,82,85,9,stage)+b"\0"*(4*COUNTS[stage])

class Hour6WindAuditTests(unittest.TestCase):
    def test_correct_utc_and_stages(self):
        result=decode(b"".join(event(x) for x in STAGES),(7,),STAGES)
        self.assertEqual(len(result),3)
    def test_hour4_replay_rejected(self):
        with self.assertRaisesRegex(ValueError,"wrong source hour"):
            decode(event(hour=6),(7,),(90,))
    def test_missing_payload_rejected(self):
        with self.assertRaisesRegex(ValueError,"truncated"):
            decode(event()[:-5],(7,),(90,))
    def test_extra_payload_rejected(self):
        with self.assertRaisesRegex(ValueError,"trailing"):
            decode(event()+b"x",(7,),(90,))
    def test_frozen_wind_limit_unchanged(self):
        self.assertEqual(FROZEN_WIND_ABS_TOL,2e-4)
    def test_large_error_exceeds_tolerance(self):
        original=struct.pack("<f",1.)*COUNTS[90]
        altered=bytearray(original)
        struct.pack_into("<f",altered,0,1.0003)
        result=compare(original,altered,90)
        self.assertEqual(result["u"]["frozen_exceedances"],1)
        self.assertEqual(result["v"]["frozen_exceedances"],0)
    def test_stage110_wface_count(self):
        zero=b"\0"*(4*COUNTS[110])
        result=compare(zero,zero,110)
        self.assertEqual(result["w"]["count"],69700)

if __name__=="__main__":
    unittest.main()
