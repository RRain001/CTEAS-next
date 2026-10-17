cmake_minimum_required(VERSION 3.20)
project(CTEAS_P6F_CALMET_DAT21_WRITER LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# ---------------------------------------------------------------------------
# P6F: CALMET.DAT 2.1 writer.
#
#   p6f_calmet_dat21            -- the writer library (explicit arrays -> bytes)
#   cteas_p6f_calmet_dat21_writer -- CLI: roundtrip | check | emit-fixture
#
# The module is standalone: it includes no P6E/P6D/P7 header. The E22 output
# contract of the P6E module is consumed only by the cross-read test below,
# through an explicit read-only include path, as an independent decoder.
# ---------------------------------------------------------------------------
add_library(p6f_calmet_dat21 STATIC
  src/calmet_dat21_writer.cpp
  src/sha256.cpp)
target_include_directories(p6f_calmet_dat21 PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)

# Input adapter for the P6D real-case wind-field array product. Kept separate so
# the writer library itself has no dependency on another track's output contract.
add_library(p6f_p6d_fields STATIC src/p6d_fields.cpp)
target_link_libraries(p6f_p6d_fields PUBLIC p6f_calmet_dat21)
target_include_directories(p6f_p6d_fields PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)

add_executable(cteas_p6f_calmet_dat21_writer src/calmet_dat21_writer_main.cpp)
target_link_libraries(cteas_p6f_calmet_dat21_writer PRIVATE p6f_calmet_dat21 p6f_p6d_fields)

# Evidence helper: documented, value-only perturbations of a legal file, so the
# original reader can be exercised on changed-but-legal numbers.
add_executable(cteas_p6f_calmet_dat21_perturb src/calmet_dat21_perturb_main.cpp)
target_link_libraries(cteas_p6f_calmet_dat21_perturb PRIVATE p6f_calmet_dat21)

# Independent provenance checker: uses the original GEO.DAT/P6C READGE
# parser and the met.inp control deck, never the CALMET.DAT static values
# as expected values. Comparator file is input only to verify source parity.
add_executable(cteas_p6f_geo_static_provenance
  src/p6f_geo_static_provenance_main.cpp)
target_link_libraries(cteas_p6f_geo_static_provenance PRIVATE p6f_calmet_dat21)
target_include_directories(cteas_p6f_geo_static_provenance PRIVATE
  "${CMAKE_CURRENT_SOURCE_DIR}/../include")

# Optional P6E reference-independent metadata input builder. This selected-case
# baseline consumes GEO.DAT + met.inp exclusively, not a reference CALMET.DAT.
# All 143h hourly payload fields are deliberately original-missing sentinels,
# so only native P6D wind + native P6E physics can provide computed values.
add_executable(cteas_p6f_p6e_source_metadata
  src/p6f_p6e_source_metadata_main.cpp)
target_link_libraries(cteas_p6f_p6e_source_metadata PRIVATE p6f_calmet_dat21)
target_include_directories(cteas_p6f_p6e_source_metadata PRIVATE
  "${CMAKE_CURRENT_SOURCE_DIR}/../include")

add_executable(p6f_calmet_dat21_writer_tests tests/calmet_dat21_writer_tests.cpp)
target_link_libraries(p6f_calmet_dat21_writer_tests PRIVATE p6f_calmet_dat21)

set(P6F_E22_INCLUDE "${CMAKE_CURRENT_SOURCE_DIR}/../p6e/include")
if(NOT EXISTS "${P6F_E22_INCLUDE}/cteas/p6e/calmet_dat21.hpp")
  message(FATAL_ERROR
    "P6F cross-read needs the E22 output contract header "
    "${P6F_E22_INCLUDE}/cteas/p6e/calmet_dat21.hpp (read-only dependency).")
endif()
add_executable(p6f_calmet_dat21_e22_cross_read_tests
  tests/calmet_dat21_e22_cross_read_tests.cpp)
target_link_libraries(p6f_calmet_dat21_e22_cross_read_tests PRIVATE p6f_calmet_dat21)
target_include_directories(p6f_calmet_dat21_e22_cross_read_tests PRIVATE ${P6F_E22_INCLUDE})

foreach(target p6f_calmet_dat21 p6f_p6d_fields cteas_p6f_calmet_dat21_writer
        cteas_p6f_calmet_dat21_perturb cteas_p6f_geo_static_provenance
        cteas_p6f_p6e_source_metadata
        p6f_calmet_dat21_writer_tests
        p6f_calmet_dat21_e22_cross_read_tests)
  if(MSVC)
    target_compile_options(${target} PRIVATE /W4 /WX)
  else()
    target_compile_options(${target} PRIVATE -Wall -Wextra -Wpedantic -Werror)
  endif()
endforeach()

enable_testing()
add_test(NAME p6f_calmet_dat21_writer_unit COMMAND p6f_calmet_dat21_writer_tests)

find_package(Python3 COMPONENTS Interpreter REQUIRED)

# Synthetic CLI end-to-end: emit-fixture -> check -> roundtrip, with an
# independent Python walk of the produced bytes and the fail-closed cases.
add_test(NAME p6f_calmet_dat21_synthetic_cli_roundtrip
  COMMAND "${Python3_EXECUTABLE}"
    "${CMAKE_CURRENT_SOURCE_DIR}/tests/verify_synthetic_cli_roundtrip.py"
    --tool "$<TARGET_FILE:cteas_p6f_calmet_dat21_writer>"
    --report "${CMAKE_CURRENT_BINARY_DIR}/p6f-synthetic-report.json")

# The frozen real 2022 reference case and the independent P7 decoder are the
# writer's ground truth: the gate is FAIL-closed when either is missing rather
# than silently skipping the byte-identity proof.
set(P6F_REPO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../../.." CACHE PATH
  "Case root for P6F pinned source provenance CTests (may be external checkout)")
set(P6F_REAL_MET_DAT
  "${P6F_REPO_ROOT}/project/cases/hefei5km_2022_reference_case_20261011/run/met/met.dat")
set(P6F_REAL_MET_SHA256
  "b1823cda92280888d70b00961ab39486036a3086e18637fff21efb4f4b237d30")
set(P6F_P7_DECODER
  "${CMAKE_CURRENT_SOURCE_DIR}/../../p7_calpuff/reference/original_decode_calmet_hourly.py")

# The locked-case static provenance gate has *independent* upstream input:
# GEO.DAT (READGE), met.inp (grid/station/projection), and no static values
# sourced from MET.DAT. Missing raw inputs are NOT silently skipped.
set(P6F_SOURCE_GEO
  "${P6F_REPO_ROOT}/project/cases/hefei5km_2022_reference_case_20261011/geo/makegeo/geo.dat")
set(P6F_SOURCE_DECK
  "${P6F_REPO_ROOT}/project/cases/hefei5km_2022_reference_case_20261011/run/met/met.inp")
foreach(source_file "${P6F_SOURCE_GEO}" "${P6F_SOURCE_DECK}")
  if(NOT EXISTS "${source_file}")
    message(FATAL_ERROR "P6F source-independent GEO/deck gate missing ${source_file}")
  endif()
endforeach()
add_test(NAME p6f_calmet_dat21_independent_geo_statics
  COMMAND cteas_p6f_geo_static_provenance
    --geo "${P6F_SOURCE_GEO}"
    --deck "${P6F_SOURCE_DECK}"
    --candidate "${P6F_REAL_MET_DAT}")

if(NOT EXISTS "${P6F_REAL_MET_DAT}")
  message(FATAL_ERROR
    "P6F byte-identity acceptance needs the frozen reference ${P6F_REAL_MET_DAT}.")
endif()
if(NOT EXISTS "${P6F_P7_DECODER}")
  message(FATAL_ERROR
    "P6F cross-read acceptance needs the P7 decoder ${P6F_P7_DECODER}.")
endif()

# read -> rewrite -> byte-for-byte identical (SHA-256 pinned) + independent
# inventory + P7 decoder cross-read + fail-closed negatives.
add_test(NAME p6f_calmet_dat21_real_reference_round_trip
  COMMAND "${Python3_EXECUTABLE}"
    "${CMAKE_CURRENT_SOURCE_DIR}/tests/verify_real_reference_roundtrip.py"
    --tool "$<TARGET_FILE:cteas_p6f_calmet_dat21_writer>"
    --p7-decoder "${P6F_P7_DECODER}"
    --real-reference "${P6F_REAL_MET_DAT}"
    --real-reference-sha256 "${P6F_REAL_MET_SHA256}"
    --report "${CMAKE_CURRENT_BINARY_DIR}/p6f-real-reference-report.json")

# The E22 contract reader must parse every record of the re-serialised frozen
# case without loss (6,435 field records compared cell by cell).
add_test(NAME p6f_calmet_dat21_e22_contract_cross_read
  COMMAND p6f_calmet_dat21_e22_cross_read_tests "${P6F_REAL_MET_DAT}")

# The P6D real-case wind-array contract: metadata.json + raw float32 planes ->
# the documented one-command entry, verified value by value against the arrays.
add_test(NAME p6f_calmet_dat21_p6d_array_input
  COMMAND "${Python3_EXECUTABLE}"
    "${CMAKE_CURRENT_SOURCE_DIR}/tests/verify_p6d_array_input.py"
    --tool "$<TARGET_FILE:cteas_p6f_calmet_dat21_writer>"
    --statics-from "${P6F_REAL_MET_DAT}"
    --report "${CMAKE_CURRENT_BINARY_DIR}/p6f-p6d-array-input-report.json")

# XMISS at real scale: 50x50x9, 143 intervals, the sentinel in every real and
# integer field, cross-checked against an independent scan and the P7 decoder.
add_test(NAME p6f_calmet_dat21_real_scale_xmiss
  COMMAND "${Python3_EXECUTABLE}"
    "${CMAKE_CURRENT_SOURCE_DIR}/tests/verify_real_scale_xmiss_round_trip.py"
    --tool "$<TARGET_FILE:cteas_p6f_calmet_dat21_writer>"
    --p7-decoder "${P6F_P7_DECODER}"
    --report "${CMAKE_CURRENT_BINARY_DIR}/p6f-real-scale-xmiss-report.json")

# The original CALPUFF read test needs a Fortran compiler and rebuilds the
# original from the unchanged vendor sources, so it is registered only where the
# toolchain exists and is run as its own fail-closed step by
# scripts/local_gate.py (a missing toolchain must never look like a pass).
# The tracked vendor Fortran only builds with the repository's Linux GNU Fortran
# recipe, so the test is registered on that toolchain only; on other hosts the
# gate step in scripts/local_gate.py still declares the toolchain in `requires`.
find_program(P6F_GFORTRAN NAMES gfortran-11 gfortran-12)
set(P6F_VENDOR_CALPUFF "${P6F_REPO_ROOT}/engine/vendor/src/CALPUFF_v7.2.1_L150618")
set(P6F_PUFF_INP "${P6F_REPO_ROOT}/project/cases/hefei5km_2022_reference_case_20261011/run/puff/puff.inp")
set(P6F_REFERENCE_CON "${P6F_REPO_ROOT}/project/cases/hefei5km_2022_reference_case_20261011/deliverables/puff/puff.con")
set(P6F_REFERENCE_LST "${P6F_REPO_ROOT}/project/cases/hefei5km_2022_reference_case_20261011/deliverables/puff/puff.lst")
if(NOT APPLE AND P6F_GFORTRAN AND EXISTS "${P6F_VENDOR_CALPUFF}/modules.for" AND
   EXISTS "${P6F_PUFF_INP}" AND EXISTS "${P6F_REFERENCE_CON}")
  add_test(NAME p6f_calmet_dat21_original_calpuff_reads_written_calmet
    COMMAND "${Python3_EXECUTABLE}"
      "${CMAKE_CURRENT_SOURCE_DIR}/tests/verify_original_calpuff_reads_written_calmet.py"
      --tool "$<TARGET_FILE:cteas_p6f_calmet_dat21_writer>"
      --perturb "$<TARGET_FILE:cteas_p6f_calmet_dat21_perturb>"
      --vendor "${P6F_VENDOR_CALPUFF}"
      --fortran "${P6F_GFORTRAN}"
      --control "${P6F_PUFF_INP}"
      --frozen-met "${P6F_REAL_MET_DAT}"
      --frozen-sha256 "${P6F_REAL_MET_SHA256}"
      --reference-con "${P6F_REFERENCE_CON}"
      --reference-lst "${P6F_REFERENCE_LST}"
      --out "${CMAKE_CURRENT_BINARY_DIR}/original-calpuff"
      --report "${CMAKE_CURRENT_BINARY_DIR}/p6f-original-calpuff-report.json")
  message(STATUS "P6F original CALPUFF read test: REGISTERED (${P6F_GFORTRAN})")
else()
  message(STATUS "P6F original CALPUFF read test: not registered here "
                 "(no Fortran compiler or inputs); scripts/local_gate.py runs it "
                 "as a fail-closed step with explicit requires")
endif()
