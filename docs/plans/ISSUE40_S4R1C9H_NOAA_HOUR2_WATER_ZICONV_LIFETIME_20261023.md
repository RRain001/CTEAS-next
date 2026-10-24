# S4-R1c9h — real NOAA second-hour global WATER ZICONV lifetime

Original, independently recompiled CALMET 6.5.0, true NOAA 2022-06-01
01–07 UTC, grid 82x85x9, 2SS/1US, 63 WATER cells. Sixhour original
MET.DAT SHA-256: a7004fbf780212d58536be3957306c2aecc53abe2e58bfec870571b12d8b8e14.
Source GEO/SURF/UP/MET.INP SHA-256:
5feaa58e5835576b3ae2c03a51e955114d620a7aeb710ded58a9f999695f602a
6a3f45eebdba8c7b783b5b89d5e1b3a7eecf2ce71f7fdaa814e7a54f04a9f655
a4e99dabe6ed246643bb298c3d883c8cde8a5dd07aaa346952f7e096d325ad00
c5e6b02ac623a3f7d11b464deca657cd26285605753ef185bcc215257dee9744
Original MAKEGEO vs native P3: 55,760 values, zero exceedances.

Root cause: original WATER() computes a LOCAL scalar ZICONV and updates
ZICOLD(I,J), but does NOT overwrite the global gridded ZICONV(I,J).
The following MIXHT() skips WATER cells. This grid memory must therefore
retain the preceding hour's post-AVEMIX ZICONV until current AVEMIX.
G63 incorrectly replaced its WATER cells with G36's local neutral
ZICONV=0. Example original previous global water values: 186.914795 m
(i=2,j=1), 442.605408 m (i=25,j=73), overwritten by zero in old native.

Old exact-source original vs native second hour: 1,397 exceedances /
313,650 values (WSTAR 630, T-LEV4/5/6/7 2/24/167/574).
Scratch original Fortran instrumentation (write-only; unchanged original
six-hour MET SHA) showed QH/TEMP2D/RHO all bitwise identical, but native
ZICONV mismatch before AVEMIX up to 442.605 m and after AVEMIX up to
223.069 m.

Fix in G63: retain live.previous.ziconv_m at WATER source ordinals
while updating genuine current-hour WATER mechanical ZI and neutral
QH/USTAR/EL; validate previous global water state finite/nonnegative.
Do not alter numerical formulas or frozen thresholds.
P6E regression checks nonzero WATER global ZICONV across MIXHT skip.
Opt-in forensic output writes exclusive scratch stage12/13, stage14,
hour1 committed memory without reference-oracle data entering native.

Fresh Ubuntu local original vs fixed C++ second hour:
PASS_SCOPED_ORIGINAL_NATIVE_HOUR2_FULL45
313,650 compared values, ZERO frozen-tolerance exceedances.
Fixed native candidate SHA256:
d0612c0fee5d25baf1c640f730e6932733ffc82d6878ba56bb7ef6b157464d82
Intermediate residual maxima: MIXHT ZICONV 0.002869 m;
post-AVEMIX ZICONV 0.001038 m. No original assets are committed.

LIMITS: Not an independent scientific audit. Hour-two G14 atomic commit,
hour3–6, production S4, Ubuntu exact-head Docker full, independent
review, C1/C2 broad regressions and P7 remain NOT_ACCEPTED.
Do not auto-merge based on this scoped local science pass.
