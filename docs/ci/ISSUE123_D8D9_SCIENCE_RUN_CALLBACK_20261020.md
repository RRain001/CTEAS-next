# Issue #123 science result callback — run observability, NOT numerical validation

2026-10-20. The authenticated real Wolsong D6B/D8/D9 science workflow runs from trusted main or explicitly authorized workflow_dispatch. Historically the dispatch broker acknowledges acceptance without returning its downstream workflow run ID, making scientific artifacts hard to locate from the linked GitHub connector.

This scoped addition reports the **actual github.run_id**, github.sha, D6 original BLN status, D8 actual original Fortran/C++ IPTYPE report status, and D9 original-vs-native 200x200x38 HITS report status in a comment on **Issue #123** after the real science job completes or fails. Only valid, bounded JSON reports and SHA strings are copied into the comment. Source, BLN, GLCC raw bytes, point arrays, original executable and full logs remain ephemeral and never appear in the issue comment.

Security: callback is limited to RRain001/CTEAS-next main, never on PR jobs. Only the real job gains the scoped GitHub issues:write permission; other jobs remain contents:read. The callback is a best-effort final step that must not turn a scientific failure into a PASS, and a callback failure must not obscure the underlying scientific status. No user inputs define destination issue or repository.

Reported labels are explicitly marked as *unverified until independent artifact/log inspection*. D10 LU.DAT fractions, additional original physical options, P3 and P6/P7 remain out of scope. #119 EXACT_AREA_V1 source and computation are unchanged.
