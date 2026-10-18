"""#54 independent original/native hit misassignment localization.

Counts only (not raw DEM, per-pixel locations or complete elevation fields).
Physically meaningful acceptance remains in compare_p1_general.py unchanged.
"""
from __future__ import annotations

def localize_hit_differences(original:list[int],native:list[int],nx:int,ny:int)->dict:
    if (nx<1 or ny<1 or len(original)!=nx*ny or len(native)!=nx*ny
        or any(type(x) is not int or x<0 for x in [*original,*native])):
        raise ValueError("invalid original/native hit-grid arrays")
    residual=[o-n for o,n in zip(original,native)]
    changed=[]
    rowcount=[0]*ny
    colcount=[0]*nx
    positive=negative=0
    for k,delta in enumerate(residual):
        if not delta:
            continue
        i,j=k%nx,k//nx
        changed.append([i+1,j+1,original[k],native[k],delta])
        rowcount[j]+=1
        colcount[i]+=1
        if delta>0:
            positive+=delta
        else:
            negative-=delta
    horizontal=vertical=0
    for j in range(ny):
        for i in range(nx):
            k=j*nx+i
            if i+1<nx and residual[k]*residual[k+1]<0:
                horizontal+=min(abs(residual[k]),abs(residual[k+1]))
            if j+1<ny and residual[k]*residual[k+nx]<0:
                vertical+=min(abs(residual[k]),abs(residual[k+nx]))
    return {
       "scope":"AGGREGATE_DIAGNOSTIC_ONLY_NO_ASSIGNMENT_REPAIR",
       "nx":nx,"ny":ny,
       "original_hits_total":sum(original),
       "native_hits_total":sum(native),
       "net_original_minus_native":sum(residual),
       "cells_mismatched":len(changed),
       "original_surplus_sample_hits":positive,
       "native_surplus_sample_hits":negative,
       "max_abs_cell_hit_difference":max(map(abs,residual),default=0),
       "mismatch_cells_per_model_row_south_to_north":rowcount,
       "mismatch_cells_per_model_column_west_to_east":colcount,
       "horizontal_adjacent_opposite_sign_candidates":horizontal,
       "vertical_adjacent_opposite_sign_candidates":vertical,
       "first30_mismatched_cells_i_j_original_native_delta":changed[:30]
    }
