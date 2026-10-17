cmake_minimum_required(VERSION 3.20)
project(CTEAS_P7_CALPUFF LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
add_library(cteas_p7_control STATIC src/control.cpp)
target_include_directories(cteas_p7_control PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
if(MSVC)
  target_compile_options(cteas_p7_control PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_control PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
enable_testing()
add_executable(cteas_p7_control_tests tests/control_tests.cpp)
target_link_libraries(cteas_p7_control_tests PRIVATE cteas_p7_control)
if(MSVC)
  target_compile_options(cteas_p7_control_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_control_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME cteas_p7_control_contract COMMAND cteas_p7_control_tests)
if(DEFINED P7_ORIGINAL_CONTROL)
  add_test(NAME cteas_p7_original_bundled_control
    COMMAND cteas_p7_control_tests ${P7_ORIGINAL_CONTROL})
endif()

add_library(cteas_p7_records STATIC src/fortran_records.cpp)
target_include_directories(cteas_p7_records PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
if(MSVC)
  target_compile_options(cteas_p7_records PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_records PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_executable(cteas_p7_records_tests tests/fortran_records_tests.cpp)
target_link_libraries(cteas_p7_records_tests PRIVATE cteas_p7_records)
if(MSVC)
  target_compile_options(cteas_p7_records_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_records_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME cteas_p7_fortran_record_contract COMMAND cteas_p7_records_tests)

add_library(cteas_p7_calmet21 STATIC src/calmet21.cpp src/gregorian.cpp src/original_met_hours.cpp)
target_include_directories(cteas_p7_calmet21 PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(cteas_p7_calmet21 PUBLIC cteas_p7_records)
if(MSVC)
  target_compile_options(cteas_p7_calmet21 PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_calmet21 PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_executable(cteas_p7_calmet21_inspect src/calmet21_inspect.cpp)
target_link_libraries(cteas_p7_calmet21_inspect PRIVATE cteas_p7_calmet21)
add_executable(cteas_p7_calmet21_tests tests/calmet21_tests.cpp)
target_link_libraries(cteas_p7_calmet21_tests PRIVATE cteas_p7_calmet21)
add_test(NAME cteas_p7_calmet21_typed_field_contract COMMAND cteas_p7_calmet21_tests)
add_executable(cteas_p7_native_met_hours src/native_met_hours_cli.cpp)
target_link_libraries(cteas_p7_native_met_hours PRIVATE cteas_p7_calmet21)
find_package(Python3 COMPONENTS Interpreter REQUIRED)
set(P7G_LOCKED_CASE_MET "${CMAKE_CURRENT_SOURCE_DIR}/../../../project/cases/hefei5km_2022_reference_case_20261011/run/met/met.dat")
if(EXISTS "${P7G_LOCKED_CASE_MET}")
  add_test(NAME cteas_p7g_locked_case_static_decode
    COMMAND cteas_p7_calmet21_tests --met "${P7G_LOCKED_CASE_MET}")
  add_test(NAME cteas_p7_original_2022_native_met_hourly_bytes
    COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tests/original_met_hourly_parity.py"
            --binary "$<TARGET_FILE:cteas_p7_native_met_hours>"
            --met "${P7G_LOCKED_CASE_MET}")
endif()

add_test(NAME cteas_p7_original_case_stage_contract
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tests/original_reference_staging_tests.py")

add_test(NAME cteas_p7_historical_2023_scope_contract
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tests/legacy_2023_scope_tests.py")

# P7C isolated constant-source / prescribed wind transport prototype;
# no dispersion/concentration equivalence until P7D/E gates.
add_library(cteas_p7_transport STATIC src/transport.cpp)
target_include_directories(cteas_p7_transport PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(cteas_p7_transport PUBLIC cteas_p7_control)
if(MSVC)
  target_compile_options(cteas_p7_transport PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_transport PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_executable(cteas_p7_transport_tests tests/transport_tests.cpp)
target_link_libraries(cteas_p7_transport_tests PRIVATE cteas_p7_transport)
add_test(NAME cteas_p7c_release_advection_inventory_contract
  COMMAND cteas_p7_transport_tests)

add_library(cteas_p7_met_replay STATIC src/met_replay.cpp)
target_include_directories(cteas_p7_met_replay PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(cteas_p7_met_replay PUBLIC cteas_p7_transport cteas_p7_calmet21)
if(MSVC)
  target_compile_options(cteas_p7_met_replay PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_met_replay PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_executable(cteas_p7c_met_replay src/met_replay_inspect.cpp)
target_link_libraries(cteas_p7c_met_replay PRIVATE cteas_p7_met_replay)

# P7 2022 Hefei 50x50/100 m case execution ledger: fail-closed frozen input
# identity and cross-file consistency. It makes no physics or parity claim.
add_library(cteas_p7_case_ledger STATIC src/sha256.cpp src/case_ledger.cpp)
target_include_directories(cteas_p7_case_ledger PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(cteas_p7_case_ledger PUBLIC cteas_p7_calmet21 cteas_p7_control)
if(MSVC)
  target_compile_options(cteas_p7_case_ledger PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_case_ledger PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_executable(cteas_p7_2022_case_ledger src/case_ledger_main.cpp)
target_link_libraries(cteas_p7_2022_case_ledger PRIVATE cteas_p7_case_ledger)
add_executable(cteas_p7_case_ledger_tests tests/case_ledger_tests.cpp)
target_link_libraries(cteas_p7_case_ledger_tests PRIVATE cteas_p7_case_ledger)
if(MSVC)
  target_compile_options(cteas_p7_case_ledger_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_case_ledger_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME cteas_p7_2022_case_ledger_contract COMMAND cteas_p7_case_ledger_tests)
add_test(NAME cteas_p7_2022_ledger_real_2023_refusal
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tests/case_ledger_real_2023_tests.py"
          --binary "$<TARGET_FILE:cteas_p7_2022_case_ledger>")

# P7D: CALPUFF 7.2.1 dispersion coefficients for the selected MDISP=3 path
# (PG rural + MP/Briggs urban). Vendor source anchors, not a physics claim.
add_library(cteas_p7_dispersion STATIC src/dispersion.cpp)
target_include_directories(cteas_p7_dispersion PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(cteas_p7_dispersion PUBLIC cteas_p7_control)
if(MSVC)
  target_compile_options(cteas_p7_dispersion PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_dispersion PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_executable(cteas_p7d_sigma_probe src/dispersion_probe.cpp)
target_link_libraries(cteas_p7d_sigma_probe PRIVATE cteas_p7_dispersion)
add_executable(cteas_p7_dispersion_tests tests/dispersion_tests.cpp)
target_link_libraries(cteas_p7_dispersion_tests PRIVATE cteas_p7_dispersion)
if(MSVC)
  target_compile_options(cteas_p7_dispersion_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_dispersion_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME cteas_p7d_dispersion_contract COMMAND cteas_p7_dispersion_tests)

add_test(NAME cteas_p7d_sigma_source_parity
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tests/sigma_fortran_parity_tests.py"
          --probe "$<TARGET_FILE:cteas_p7d_sigma_probe>"
          --repo-root "${CMAKE_CURRENT_SOURCE_DIR}/../../..")

# P7: Original turbulence-based IDOPT=1 CALPUFF calm subset, EL<=0.
# Original compiled Fortran parity is a separate mandatory acceptance gate.
add_executable(cteas_p7_calm_sigma_probe src/original_calm_sigma_probe.cpp)
add_executable(cteas_p7_calm_sigma_tests tests/original_calm_sigma_tests.cpp)
target_include_directories(cteas_p7_calm_sigma_probe PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_include_directories(cteas_p7_calm_sigma_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)
if(MSVC)
  target_compile_options(cteas_p7_calm_sigma_probe PRIVATE /W4 /WX)
  target_compile_options(cteas_p7_calm_sigma_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_calm_sigma_probe PRIVATE -Wall -Wextra -Wpedantic -Werror)
  target_compile_options(cteas_p7_calm_sigma_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME cteas_p7_calm_idopt1_native_subset
  COMMAND cteas_p7_calm_sigma_tests)
add_test(NAME cteas_p7_calm_idopt1_original_fortran_subset
  COMMAND "${Python3_EXECUTABLE}"
    "${CMAKE_CURRENT_SOURCE_DIR}/tests/calm_sigma_fortran_parity_tests.py"
    --probe "$<TARGET_FILE:cteas_p7_calm_sigma_probe>"
    --repo-root "${CMAKE_CURRENT_SOURCE_DIR}/../../..")

# Original CALPUFF MDISP=3 calm TURBSET fallback from original Hefei
# SVMIN/SWMIN arrays, never an inferred land/water category.
add_executable(cteas_p7_original_turbset_mdisp3_tests
  tests/original_turbset_mdisp3_tests.cpp)
target_include_directories(cteas_p7_original_turbset_mdisp3_tests PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(cteas_p7_original_turbset_mdisp3_tests PRIVATE
  cteas_p7_control cteas_p7_calmet21)
if(MSVC)
  target_compile_options(cteas_p7_original_turbset_mdisp3_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_original_turbset_mdisp3_tests PRIVATE
    -Wall -Wextra -Wpedantic -Werror)
endif()
set(P7_CALM_HEFEI_CONTROL
  "${CMAKE_CURRENT_SOURCE_DIR}/../../../project/cases/hefei5km_2022_reference_case_20261011/run/puff/puff.inp")
set(P7_CALM_HEFEI_MAKEGEO
  "${CMAKE_CURRENT_SOURCE_DIR}/../../../project/cases/hefei5km_2022_reference_case_20261011/geo/makegeo/makegeo.inp")
if(EXISTS "${P7_CALM_HEFEI_CONTROL}" AND
   EXISTS "${P7_CALM_HEFEI_MAKEGEO}" AND EXISTS "${P7G_LOCKED_CASE_MET}")
  add_test(NAME cteas_p7_original_turbset_mdisp3_hefei_minima
    COMMAND cteas_p7_original_turbset_mdisp3_tests
      "${P7_CALM_HEFEI_CONTROL}" "${P7_CALM_HEFEI_MAKEGEO}" "${P7G_LOCKED_CASE_MET}")
endif()

# P7F: CALPUFF 7.2.1 MDRY=1 dry deposition for the selected real-case species
# methods (H-3 computed gas, HE-3 no removal).
add_library(cteas_p7_dry_deposition STATIC src/dry_deposition.cpp)
target_include_directories(cteas_p7_dry_deposition PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(cteas_p7_dry_deposition PUBLIC cteas_p7_control)
if(MSVC)
  target_compile_options(cteas_p7_dry_deposition PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_dry_deposition PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_executable(cteas_p7f_drydep_probe src/drydep_probe.cpp)
target_link_libraries(cteas_p7f_drydep_probe PRIVATE cteas_p7_dry_deposition cteas_p7_calmet21)
add_executable(cteas_p7_dry_deposition_tests tests/dry_deposition_tests.cpp)
target_link_libraries(cteas_p7_dry_deposition_tests PRIVATE cteas_p7_dry_deposition)
if(MSVC)
  target_compile_options(cteas_p7_dry_deposition_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_dry_deposition_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME cteas_p7f_dry_deposition_contract COMMAND cteas_p7_dry_deposition_tests)
set(P7F_LOCKED_CASE_CONTROL "${CMAKE_CURRENT_SOURCE_DIR}/../../../project/cases/hefei5km_2022_reference_case_20261011/run/puff/puff.inp")
# Mode A: the *frozen original CALPUFF control* owns the selected point-source
# coordinates and stack parameters. Never restore extra lon/lat -> UTM digits
# from a preprocessing CSV, Python variable, or notebook during source parity.
# Fail at configure time if the selected, single-source deck is malformed.
if(EXISTS "${P7F_LOCKED_CASE_CONTROL}")
  file(STRINGS "${P7F_LOCKED_CASE_CONTROL}" P7_ORIGINAL_POINT_SOURCE_ROWS
    REGEX "^[ \t]*1[ \t]+![ \t]*X[ \t]*=")
  list(LENGTH P7_ORIGINAL_POINT_SOURCE_ROWS P7_ORIGINAL_POINT_SOURCE_COUNT)
  if(NOT P7_ORIGINAL_POINT_SOURCE_COUNT EQUAL 1)
    message(FATAL_ERROR "P7 original-compatible deck needs exactly one active point source X row")
  endif()
  list(GET P7_ORIGINAL_POINT_SOURCE_ROWS 0 P7_ORIGINAL_POINT_SOURCE_ROW)
  string(REGEX MATCH
    "X[ \t]*=[ \t]*([^,]+),[ \t]*([^,]+),[ \t]*([^,]+),[ \t]*([^,]+),[ \t]*([^,]+),[ \t]*([^,]+),[ \t]*([^,]+),[ \t]*([^,]+),[ \t]*([^,]+),"
    P7_ORIGINAL_POINT_SOURCE_MATCH "${P7_ORIGINAL_POINT_SOURCE_ROW}")
  if(NOT P7_ORIGINAL_POINT_SOURCE_MATCH)
    message(FATAL_ERROR "P7 original-compatible point-source coordinates/stack parameters are malformed")
  endif()
  set(P7_STACK_X_KM "${CMAKE_MATCH_1}")
  set(P7_STACK_Y_KM "${CMAKE_MATCH_2}")
  set(P7_STACK_HEIGHT_M "${CMAKE_MATCH_3}")
  set(P7_STACK_BASE_M "${CMAKE_MATCH_4}")
  set(P7_STACK_DIAMETER_M "${CMAKE_MATCH_5}")
  set(P7_STACK_EXIT_MS "${CMAKE_MATCH_6}")
  set(P7_STACK_TEMP_K "${CMAKE_MATCH_7}")
  set(P7_STACK_DOWNWASH "${CMAKE_MATCH_8}")
  set(P7_STACK_Q1 "${CMAKE_MATCH_9}")
  foreach(P7_STACK_PARAMETER X_KM Y_KM HEIGHT_M BASE_M DIAMETER_M EXIT_MS TEMP_K DOWNWASH Q1)
    string(STRIP "${P7_STACK_${P7_STACK_PARAMETER}}" P7_STACK_${P7_STACK_PARAMETER})
  endforeach()
  # The input parser runs even when the (large) frozen MET.DAT is not checked out.
  # A missing control does not silently turn a hard-coded coordinate into evidence.
  add_test(NAME cteas_p7c_locked_original_point_input
    COMMAND cteas_p7_transport_tests "${P7F_LOCKED_CASE_CONTROL}")
endif()
if(EXISTS "${P7F_LOCKED_CASE_CONTROL}")
  add_test(NAME cteas_p7f_locked_case_dry_deposition
    COMMAND cteas_p7_dry_deposition_tests --control "${P7F_LOCKED_CASE_CONTROL}")
endif()
# P7E: receptor geometry, puff-to-receptor sampling and CONC.DAT framing.
add_library(cteas_p7_receptors STATIC src/receptors.cpp src/conc_file.cpp src/hourly_conc.cpp)
target_include_directories(cteas_p7_receptors PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(cteas_p7_receptors PUBLIC cteas_p7_control cteas_p7_records)
if(MSVC)
  target_compile_options(cteas_p7_receptors PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_receptors PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_executable(cteas_p7e_probe src/p7e_probe.cpp)
target_link_libraries(cteas_p7e_probe PRIVATE cteas_p7_receptors)
add_executable(cteas_p7e_tests tests/p7e_tests.cpp)
target_link_libraries(cteas_p7e_tests PRIVATE cteas_p7_receptors)
if(MSVC)
  target_compile_options(cteas_p7e_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7e_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
# Streaming P7E WROUT1 hourly DATA section: exact timestamp continuity and
# REAL*4 field payload preservation. This does not construct original header
# tables nor calculate native concentrations.
add_executable(cteas_p7_hourly_conc_tests tests/hourly_conc_tests.cpp)
target_link_libraries(cteas_p7_hourly_conc_tests PRIVATE cteas_p7_receptors)
if(MSVC)
  target_compile_options(cteas_p7_hourly_conc_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_hourly_conc_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME cteas_p7e_native_143h_hourly_data_writer_contract
         COMMAND cteas_p7_hourly_conc_tests)
set(P7E_LOCKED_CASE_CONC "${CMAKE_CURRENT_SOURCE_DIR}/../../../project/cases/hefei5km_2022_reference_case_20261011/run/puff/puff.con")
if(EXISTS "${P7E_LOCKED_CASE_CONC}" AND EXISTS "${P7F_LOCKED_CASE_CONTROL}"
   AND EXISTS "${P7G_LOCKED_CASE_MET}")
  add_test(NAME cteas_p7e_original_wrout1_full_native_header
    COMMAND cteas_p7_hourly_conc_tests
      --frozen "${P7E_LOCKED_CASE_CONC}" "${P7F_LOCKED_CASE_CONTROL}"
               "${P7G_LOCKED_CASE_MET}")
endif()
if(EXISTS "${P7E_LOCKED_CASE_CONC}")
  # P7H: vertical coupling coefficients (VCOUP/VCBAR/CTADJ) of the concentration path.
add_library(cteas_p7_coupling STATIC src/coupling.cpp)
target_include_directories(cteas_p7_coupling PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(cteas_p7_coupling PUBLIC cteas_p7_control)
if(MSVC)
  target_compile_options(cteas_p7_coupling PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_coupling PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
target_link_libraries(cteas_p7_receptors PUBLIC cteas_p7_coupling)
target_link_libraries(cteas_p7e_probe PRIVATE cteas_p7_coupling cteas_p7_calmet21 cteas_p7_dispersion)
add_executable(cteas_p7h_tests tests/p7h_tests.cpp)
target_link_libraries(cteas_p7h_tests PRIVATE cteas_p7_coupling cteas_p7_receptors)
if(MSVC)
  target_compile_options(cteas_p7h_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7h_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME cteas_p7h_vertical_coupling_contract COMMAND cteas_p7h_tests)

# P7I: CTSG support blocks (QATR integrator, TFAC terrain factors).
add_library(cteas_p7_ctsg STATIC src/ctsg.cpp)
target_include_directories(cteas_p7_ctsg PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
# P7M: PUFFC uses the ERFDIF port that lives with the P7E sampling module.
target_link_libraries(cteas_p7_ctsg PUBLIC cteas_p7_receptors)
if(MSVC)
  target_compile_options(cteas_p7_ctsg PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_ctsg PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_executable(cteas_p7i_tests tests/p7i_tests.cpp)
target_link_libraries(cteas_p7i_tests PRIVATE cteas_p7_ctsg)
if(MSVC)
  target_compile_options(cteas_p7i_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7i_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME cteas_p7i_ctsg_support_contract COMMAND cteas_p7i_tests)
add_test(NAME cteas_p7i_source_parity
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tests/p7i_parity_tests.py"
          --probe "$<TARGET_FILE:cteas_p7i_tests>"
          --repo-root "${CMAKE_CURRENT_SOURCE_DIR}/../../..")
add_test(NAME cteas_p7h_source_parity
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tests/p7h_parity_tests.py"
          --probe "$<TARGET_FILE:cteas_p7e_probe>"
          --repo-root "${CMAKE_CURRENT_SOURCE_DIR}/../../..")

add_test(NAME cteas_p7e_receptor_sampling_conc_contract
    COMMAND cteas_p7e_tests --control "${P7F_LOCKED_CASE_CONTROL}" --frozen-conc "${P7E_LOCKED_CASE_CONC}")
else()
  # P7H: vertical coupling coefficients (VCOUP/VCBAR/CTADJ) of the concentration path.
add_library(cteas_p7_coupling STATIC src/coupling.cpp)
target_include_directories(cteas_p7_coupling PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(cteas_p7_coupling PUBLIC cteas_p7_control)
if(MSVC)
  target_compile_options(cteas_p7_coupling PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_coupling PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
target_link_libraries(cteas_p7_receptors PUBLIC cteas_p7_coupling)
target_link_libraries(cteas_p7e_probe PRIVATE cteas_p7_coupling cteas_p7_calmet21 cteas_p7_dispersion)
add_executable(cteas_p7h_tests tests/p7h_tests.cpp)
target_link_libraries(cteas_p7h_tests PRIVATE cteas_p7_coupling cteas_p7_receptors)
if(MSVC)
  target_compile_options(cteas_p7h_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7h_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME cteas_p7h_vertical_coupling_contract COMMAND cteas_p7h_tests)

# P7I: CTSG support blocks (QATR integrator, TFAC terrain factors).
add_library(cteas_p7_ctsg STATIC src/ctsg.cpp)
target_include_directories(cteas_p7_ctsg PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
# P7M: PUFFC uses the ERFDIF port that lives with the P7E sampling module.
target_link_libraries(cteas_p7_ctsg PUBLIC cteas_p7_receptors)
if(MSVC)
  target_compile_options(cteas_p7_ctsg PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_ctsg PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_executable(cteas_p7i_tests tests/p7i_tests.cpp)
target_link_libraries(cteas_p7i_tests PRIVATE cteas_p7_ctsg)
if(MSVC)
  target_compile_options(cteas_p7i_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7i_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME cteas_p7i_ctsg_support_contract COMMAND cteas_p7i_tests)
add_test(NAME cteas_p7i_source_parity
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tests/p7i_parity_tests.py"
          --probe "$<TARGET_FILE:cteas_p7i_tests>"
          --repo-root "${CMAKE_CURRENT_SOURCE_DIR}/../../..")
add_test(NAME cteas_p7h_source_parity
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tests/p7h_parity_tests.py"
          --probe "$<TARGET_FILE:cteas_p7e_probe>"
          --repo-root "${CMAKE_CURRENT_SOURCE_DIR}/../../..")

add_test(NAME cteas_p7e_receptor_sampling_conc_contract COMMAND cteas_p7e_tests)
endif()
add_test(NAME cteas_p7e_source_parity
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tests/p7e_parity_tests.py"
          --probe "$<TARGET_FILE:cteas_p7e_probe>"
          --repo-root "${CMAKE_CURRENT_SOURCE_DIR}/../../..")

add_test(NAME cteas_p7f_drydep_source_parity
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tests/drydep_parity_tests.py"
          --probe "$<TARGET_FILE:cteas_p7f_drydep_probe>"
          --repo-root "${CMAKE_CURRENT_SOURCE_DIR}/../../..")

# P7M: CTSG kernel (MUNU/IREG/BI/BJI/BJIL/SIGMA/CTREC/PUFFC/LOWER/CTSG) with the
# unmodified-vendor-source oracle. CTPAR and UPPER are NOT ported and the port
# fails closed when the vendor would call them.
add_executable(cteas_p7m_tests tests/p7m_tests.cpp)
target_link_libraries(cteas_p7m_tests PRIVATE cteas_p7_ctsg)
if(MSVC)
  target_compile_options(cteas_p7m_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7m_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME cteas_p7m_ctsg_kernel_contract COMMAND cteas_p7m_tests)

add_executable(cteas_p7m_probe src/ctsg_probe.cpp)
target_link_libraries(cteas_p7m_probe PRIVATE cteas_p7_ctsg cteas_p7_calmet21
  cteas_p7_dispersion cteas_p7_receptors cteas_p7_coupling)
add_test(NAME cteas_p7m_source_parity
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tests/p7m_parity_tests.py"
          --probe "$<TARGET_FILE:cteas_p7m_probe>"
          --repo-root "${CMAKE_CURRENT_SOURCE_DIR}/../../..")
if(EXISTS "${P7G_LOCKED_CASE_MET}" AND EXISTS "${P7F_LOCKED_CASE_CONTROL}")
  add_test(NAME cteas_p7m_real_grid_ctsg
    COMMAND cteas_p7m_probe --real-grid "${P7G_LOCKED_CASE_MET}" "${P7F_LOCKED_CASE_CONTROL}"
            0 2.63e13 ${P7_STACK_X_KM} ${P7_STACK_Y_KM} ${P7_STACK_HEIGHT_M})
endif()

# P7N: CALPUFF 7.2.1 plume rise (STKTIP/PRB/PRM/PRFIN/PRFPP/GRISE plus the
# verbatim POINTS1 flux statements) for the locked deck's gradual-rise path.
add_library(cteas_p7_plume_rise STATIC src/plume_rise.cpp)
target_include_directories(cteas_p7_plume_rise PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
if(MSVC)
  target_compile_options(cteas_p7_plume_rise PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_plume_rise PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_executable(cteas_p7n_tests tests/p7n_tests.cpp)
target_link_libraries(cteas_p7n_tests PRIVATE cteas_p7_plume_rise)
if(MSVC)
  target_compile_options(cteas_p7n_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7n_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME cteas_p7n_plume_rise_contract COMMAND cteas_p7n_tests)

add_executable(cteas_p7n_probe src/plume_rise_probe.cpp)
target_link_libraries(cteas_p7n_probe PRIVATE cteas_p7_plume_rise cteas_p7_calmet21
  cteas_p7_control)
add_test(NAME cteas_p7n_source_parity
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tests/p7n_parity_tests.py"
          --probe "$<TARGET_FILE:cteas_p7n_probe>"
          --repo-root "${CMAKE_CURRENT_SOURCE_DIR}/../../..")
if(EXISTS "${P7G_LOCKED_CASE_MET}" AND EXISTS "${P7F_LOCKED_CASE_CONTROL}")
  add_test(NAME cteas_p7n_locked_case_rise
    COMMAND cteas_p7n_probe --deck-rise "${P7G_LOCKED_CASE_MET}" "${P7F_LOCKED_CASE_CONTROL}"
            0 ${P7_STACK_X_KM} ${P7_STACK_Y_KM} ${P7_STACK_HEIGHT_M} ${P7_STACK_DIAMETER_M} ${P7_STACK_EXIT_MS} ${P7_STACK_TEMP_K})
endif()

# P7O: the release scheduler (INJECT + the verbatim POINTS1 cadence and
# release-state statements + the vendor puff-age rule).
add_library(cteas_p7_release STATIC src/release.cpp)
target_include_directories(cteas_p7_release PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
if(MSVC)
  target_compile_options(cteas_p7_release PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_release PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_executable(cteas_p7o_tests tests/p7o_tests.cpp)
target_link_libraries(cteas_p7o_tests PRIVATE cteas_p7_release)
if(MSVC)
  target_compile_options(cteas_p7o_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7o_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME cteas_p7o_release_scheduler_contract COMMAND cteas_p7o_tests)

add_executable(cteas_p7o_probe src/release_probe.cpp)
target_link_libraries(cteas_p7o_probe PRIVATE cteas_p7_release cteas_p7_plume_rise
  cteas_p7_calmet21 cteas_p7_control)
add_test(NAME cteas_p7o_source_parity
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tests/p7o_parity_tests.py"
          --probe "$<TARGET_FILE:cteas_p7o_probe>"
          --repo-root "${CMAKE_CURRENT_SOURCE_DIR}/../../..")
if(EXISTS "${P7G_LOCKED_CASE_MET}" AND EXISTS "${P7F_LOCKED_CASE_CONTROL}")
  add_test(NAME cteas_p7o_locked_case_release
    COMMAND cteas_p7o_probe --deck-release "${P7G_LOCKED_CASE_MET}" "${P7F_LOCKED_CASE_CONTROL}"
            0 ${P7_STACK_X_KM} ${P7_STACK_Y_KM} ${P7_STACK_HEIGHT_M} ${P7_STACK_DIAMETER_M} ${P7_STACK_EXIT_MS} ${P7_STACK_TEMP_K} ${P7_STACK_Q1})
endif()

# P7P: SETPUF's per-step bookkeeping (distance/travel time/calm, settling and the
# step counters) plus SETCSIG's /CSIGMA/ selection state.
add_library(cteas_p7_step STATIC src/step.cpp)
target_include_directories(cteas_p7_step PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
if(MSVC)
  target_compile_options(cteas_p7_step PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_step PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_executable(cteas_p7p_tests tests/p7p_tests.cpp)
target_link_libraries(cteas_p7p_tests PRIVATE cteas_p7_step)
if(MSVC)
  target_compile_options(cteas_p7p_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7p_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME cteas_p7p_step_bookkeeping_contract COMMAND cteas_p7p_tests)

add_executable(cteas_p7p_probe src/step_probe.cpp)
target_link_libraries(cteas_p7p_probe PRIVATE cteas_p7_step cteas_p7_calmet21
  cteas_p7_control cteas_p7_dispersion)
add_test(NAME cteas_p7p_source_parity
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tests/p7p_parity_tests.py"
          --probe "$<TARGET_FILE:cteas_p7p_probe>"
          --repo-root "${CMAKE_CURRENT_SOURCE_DIR}/../../..")
if(EXISTS "${P7G_LOCKED_CASE_MET}" AND EXISTS "${P7F_LOCKED_CASE_CONTROL}")
  add_test(NAME cteas_p7p_locked_case_step
    COMMAND cteas_p7p_probe --deck-step "${P7G_LOCKED_CASE_MET}" "${P7F_LOCKED_CASE_CONTROL}"
            0 ${P7_STACK_X_KM} ${P7_STACK_Y_KM} ${P7_STACK_HEIGHT_M})
endif()

# P7Q: SETPUF's sigma update (begin/mid/end sigmas and virtuals, the final
# adjustments and the stores) for the non-PRIME branch.
add_library(cteas_p7_sigma_update STATIC src/sigma_update.cpp)
target_include_directories(cteas_p7_sigma_update PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
if(MSVC)
  target_compile_options(cteas_p7_sigma_update PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_sigma_update PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_executable(cteas_p7q_tests tests/p7q_tests.cpp)
target_link_libraries(cteas_p7q_tests PRIVATE cteas_p7_sigma_update)
if(MSVC)
  target_compile_options(cteas_p7q_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7q_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME cteas_p7q_sigma_update_contract COMMAND cteas_p7q_tests)

add_executable(cteas_p7q_probe src/sigma_update_probe.cpp)
target_link_libraries(cteas_p7q_probe PRIVATE cteas_p7_sigma_update cteas_p7_calmet21
  cteas_p7_control cteas_p7_dispersion)
add_test(NAME cteas_p7q_source_parity
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tests/p7q_parity_tests.py"
          --probe "$<TARGET_FILE:cteas_p7q_probe>"
          --repo-root "${CMAKE_CURRENT_SOURCE_DIR}/../../..")
if(EXISTS "${P7G_LOCKED_CASE_MET}" AND EXISTS "${P7F_LOCKED_CASE_CONTROL}")
  add_test(NAME cteas_p7q_locked_case_sigma
    COMMAND cteas_p7q_probe --deck-sigma "${P7G_LOCKED_CASE_MET}" "${P7F_LOCKED_CASE_CONTROL}"
            0 ${P7_STACK_X_KM} ${P7_STACK_Y_KM} ${P7_STACK_HEIGHT_M} 1.0 1.0 100.0)
endif()

# P7R: the MCTADJ=2 terrain constraints (CTADJ2 strain, WALLTRAP valley).
add_library(cteas_p7_terrain STATIC src/terrain_constraints.cpp)
target_include_directories(cteas_p7_terrain PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
# MCTADJ2-optional SETPUF: compiled original CTADJ2 is a new dependency.
target_link_libraries(cteas_p7_sigma_update PUBLIC cteas_p7_terrain)
if(MSVC)
  target_compile_options(cteas_p7_terrain PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_terrain PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_executable(cteas_p7r_tests tests/p7r_tests.cpp)
target_link_libraries(cteas_p7r_tests PRIVATE cteas_p7_terrain)
if(MSVC)
  target_compile_options(cteas_p7r_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7r_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME cteas_p7r_terrain_constraints_contract COMMAND cteas_p7r_tests)

add_executable(cteas_p7r_probe src/terrain_probe.cpp)
target_link_libraries(cteas_p7r_probe PRIVATE cteas_p7_terrain cteas_p7_calmet21
  cteas_p7_control)
add_test(NAME cteas_p7r_source_parity
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tests/p7r_parity_tests.py"
          --probe "$<TARGET_FILE:cteas_p7r_probe>"
          --repo-root "${CMAKE_CURRENT_SOURCE_DIR}/../../..")
if(EXISTS "${P7G_LOCKED_CASE_MET}" AND EXISTS "${P7F_LOCKED_CASE_CONTROL}")
  add_test(NAME cteas_p7r_locked_case_terrain
    COMMAND cteas_p7r_probe --deck-terrain "${P7G_LOCKED_CASE_MET}" "${P7F_LOCKED_CASE_CONTROL}"
            0 ${P7_STACK_X_KM} ${P7_STACK_Y_KM} ${P7_STACK_HEIGHT_M} 89.152 0.9 1.396 0.02)
endif()

# P7S: the terrain-state producers (TERAVG strip average, TRELIEF relief and
# GETELEV elevation interpolation).
add_library(cteas_p7_terrain_state STATIC src/terrain_relief.cpp)
target_include_directories(cteas_p7_terrain_state PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
if(MSVC)
  target_compile_options(cteas_p7_terrain_state PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_terrain_state PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_executable(cteas_p7s_tests tests/p7s_tests.cpp)
target_link_libraries(cteas_p7s_tests PRIVATE cteas_p7_terrain_state)
if(MSVC)
  target_compile_options(cteas_p7s_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7s_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME cteas_p7s_terrain_state_contract COMMAND cteas_p7s_tests)

add_executable(cteas_p7s_probe src/terrain_state_probe.cpp)
target_link_libraries(cteas_p7s_probe PRIVATE cteas_p7_terrain_state cteas_p7_terrain
  cteas_p7_calmet21 cteas_p7_control)
add_test(NAME cteas_p7s_source_parity
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tests/p7s_parity_tests.py"
          --probe "$<TARGET_FILE:cteas_p7s_probe>"
          --repo-root "${CMAKE_CURRENT_SOURCE_DIR}/../../..")
if(EXISTS "${P7G_LOCKED_CASE_MET}" AND EXISTS "${P7F_LOCKED_CASE_CONTROL}")
  add_test(NAME cteas_p7s_locked_case_relief
    COMMAND cteas_p7s_probe --deck-relief "${P7G_LOCKED_CASE_MET}" "${P7F_LOCKED_CASE_CONTROL}"
            0 ${P7_STACK_X_KM} ${P7_STACK_Y_KM} ${P7_STACK_HEIGHT_M} 89.152 0.9 1.396 0.02)
endif()

# P7T: VWIDTH, the valley-width table producer consumed by WALLTRAP.
add_library(cteas_p7_valley_width STATIC src/terrain_width.cpp)
target_include_directories(cteas_p7_valley_width PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
if(MSVC)
  target_compile_options(cteas_p7_valley_width PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_valley_width PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_executable(cteas_p7t_tests tests/p7t_tests.cpp)
target_link_libraries(cteas_p7t_tests PRIVATE cteas_p7_valley_width)
if(MSVC)
  target_compile_options(cteas_p7t_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7t_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME cteas_p7t_valley_width_contract COMMAND cteas_p7t_tests)

add_executable(cteas_p7t_probe src/terrain_width_probe.cpp)
target_link_libraries(cteas_p7t_probe PRIVATE cteas_p7_valley_width cteas_p7_terrain
  cteas_p7_terrain_state cteas_p7_calmet21 cteas_p7_control)
add_test(NAME cteas_p7t_source_parity
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tests/p7t_parity_tests.py"
          --probe "$<TARGET_FILE:cteas_p7t_probe>"
          --repo-root "${CMAKE_CURRENT_SOURCE_DIR}/../../..")
if(EXISTS "${P7G_LOCKED_CASE_MET}" AND EXISTS "${P7F_LOCKED_CASE_CONTROL}")
  add_test(NAME cteas_p7t_locked_case_valley
    COMMAND cteas_p7t_probe --deck-valley "${P7G_LOCKED_CASE_MET}" "${P7F_LOCKED_CASE_CONTROL}"
            0 ${P7_STACK_X_KM} ${P7_STACK_Y_KM} ${P7_STACK_HEIGHT_M})
endif()

# P7V: the advection units (ZFIND, ADVWND, ADVECT, PUFFDZ).
add_library(cteas_p7_advection STATIC src/advection.cpp)
target_include_directories(cteas_p7_advection PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
if(MSVC)
  target_compile_options(cteas_p7_advection PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_advection PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_executable(cteas_p7v_tests tests/p7v_tests.cpp)
target_link_libraries(cteas_p7v_tests PRIVATE cteas_p7_advection)
if(MSVC)
  target_compile_options(cteas_p7v_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7v_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME cteas_p7v_advection_contract COMMAND cteas_p7v_tests)

add_executable(cteas_p7v_probe src/advection_probe.cpp)
target_link_libraries(cteas_p7v_probe PRIVATE cteas_p7_advection cteas_p7_calmet21 cteas_p7_control)
add_test(NAME cteas_p7v_source_parity
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tests/p7v_parity_tests.py"
          --probe "$<TARGET_FILE:cteas_p7v_probe>"
          --repo-root "${CMAKE_CURRENT_SOURCE_DIR}/../../..")
if(EXISTS "${P7G_LOCKED_CASE_MET}" AND EXISTS "${P7F_LOCKED_CASE_CONTROL}")
  add_test(NAME cteas_p7v_locked_case_advection
    COMMAND cteas_p7v_probe --deck-advection "${P7G_LOCKED_CASE_MET}" "${P7F_LOCKED_CASE_CONTROL}"
            0 ${P7_STACK_X_KM} ${P7_STACK_Y_KM} ${P7_STACK_HEIGHT_M} 89.152)
endif()

# P7W: RISEWIND and the one-step numerical comparison against the vendor's
# instrumented puff-step dump.
add_library(cteas_p7_rise_wind STATIC src/rise_wind.cpp)
target_include_directories(cteas_p7_rise_wind PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(cteas_p7_rise_wind PUBLIC cteas_p7_advection)
if(MSVC)
  target_compile_options(cteas_p7_rise_wind PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_rise_wind PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_executable(cteas_p7w_tests tests/p7w_tests.cpp)
target_link_libraries(cteas_p7w_tests PRIVATE cteas_p7_rise_wind)
if(MSVC)
  target_compile_options(cteas_p7w_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7w_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME cteas_p7w_rise_wind_contract COMMAND cteas_p7w_tests)

add_library(cteas_p7_step_integration STATIC src/step_integration.cpp)
target_include_directories(cteas_p7_step_integration PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
if(MSVC)
  target_compile_options(cteas_p7_step_integration PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_step_integration PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()

add_test(NAME cteas_p7g_conc_structure
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tests/p7g_structure_tests.py"
          --probe "$<TARGET_FILE:cteas_p7e_probe>"
          --repo-root "${CMAKE_CURRENT_SOURCE_DIR}/../../..")

add_executable(cteas_p7x_tests tests/p7x_tests.cpp)
target_link_libraries(cteas_p7x_tests PRIVATE cteas_p7_step_integration)
if(MSVC)
  target_compile_options(cteas_p7x_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7x_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME cteas_p7x_step_integration_contract COMMAND cteas_p7x_tests)

add_executable(cteas_p7w_probe src/puff_step_probe.cpp)
target_link_libraries(cteas_p7w_probe PRIVATE cteas_p7_rise_wind cteas_p7_step_integration
  cteas_p7_advection cteas_p7_plume_rise cteas_p7_calmet21 cteas_p7_control)
add_test(NAME cteas_p7w_source_parity
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tests/p7w_parity_tests.py"
          --probe "$<TARGET_FILE:cteas_p7w_probe>"
          --repo-root "${CMAKE_CURRENT_SOURCE_DIR}/../../..")
if(EXISTS "${P7G_LOCKED_CASE_MET}" AND EXISTS "${P7F_LOCKED_CASE_CONTROL}"
   AND EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/reference/dgm_p7_advection_2022/dgm_puffstep_hour202200100.bin")
  add_test(NAME cteas_p7w_dgm_step_comparison
    COMMAND cteas_p7w_probe --dgm-steps
            "${CMAKE_CURRENT_SOURCE_DIR}/reference/dgm_p7_advection_2022/dgm_puffstep_hour202200100.bin"
            "${P7G_LOCKED_CASE_MET}" "${P7F_LOCKED_CASE_CONTROL}"
            "${P7_STACK_X_KM}" "${P7_STACK_Y_KM}" "${P7_STACK_HEIGHT_M}" "${P7_STACK_DIAMETER_M}" "${P7_STACK_EXIT_MS}" "${P7_STACK_TEMP_K}")
endif()

# P7 Mode A: use the original CALPUFF 2022 QA output itself to establish
# REAL*4 point and all 2500 gridded-receptor XY coordinates. It is a scoped
# output-frame oracle, not a full XPT1GRD/YPT1GRD or puff.con acceptance.
set(P7_QA_2022_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/../../../project/cases/hefei5km_2022_reference_case_20261011/run/puff")
if(EXISTS "${P7F_LOCKED_CASE_CONTROL}"
   AND EXISTS "${P7_QA_2022_DIRECTORY}/qapnts.dat"
   AND EXISTS "${P7_QA_2022_DIRECTORY}/qarecg.dat")
  add_executable(cteas_p7_original_grid_qa_tests tests/original_grid_qa_tests.cpp)
  target_link_libraries(cteas_p7_original_grid_qa_tests PRIVATE cteas_p7_transport cteas_p7_receptors)
  if(MSVC)
    target_compile_options(cteas_p7_original_grid_qa_tests PRIVATE /W4 /WX)
  else()
    target_compile_options(cteas_p7_original_grid_qa_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
  endif()
  add_test(NAME cteas_p7_original_2022_qa_real4_coordinates
    COMMAND cteas_p7_original_grid_qa_tests
      "${P7F_LOCKED_CASE_CONTROL}"
      "${P7_QA_2022_DIRECTORY}/qapnts.dat"
      "${P7_QA_2022_DIRECTORY}/qarecg.dat")
endif()

# Original CTEAS engine/preprocess/grid is the AUTHORING entry. Verify its
# frozen grid.cmn/center_location only as provenance for the authoritative
# runtime puff.inp; P7 must never project center lon/lat again at runtime.
set(P7_ORIGINAL_GRID_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../../../project/cases/hefei5km_2022_reference_case_20261011/grid")
if(EXISTS "${P7F_LOCKED_CASE_CONTROL}"
   AND EXISTS "${P7_ORIGINAL_GRID_DIR}/grid.cmn"
   AND EXISTS "${P7_ORIGINAL_GRID_DIR}/center_location")
  add_test(NAME cteas_p7_original_grid_preprocess_contract
    COMMAND "${Python3_EXECUTABLE}"
      "${CMAKE_CURRENT_SOURCE_DIR}/tests/p7_grid_preprocess_contract.py"
      --grid "${P7_ORIGINAL_GRID_DIR}/grid.cmn"
      --puff "${P7F_LOCKED_CASE_CONTROL}"
      --center "${P7_ORIGINAL_GRID_DIR}/center_location"
      --negative)
endif()

# Stronger P7 original input gate: use the ACTUAL CALMET.DAT binary header
# rather than the fixed synthetic REAL*4 frame. Proves the frozen runtime
# MET.DAT, CALPUFF control and grid.cmn authoring geometry coexist correctly.
if(EXISTS "${P7G_LOCKED_CASE_MET}" AND EXISTS "${P7F_LOCKED_CASE_CONTROL}"
   AND EXISTS "${P7_ORIGINAL_GRID_DIR}/grid.cmn"
   AND EXISTS "${P7_QA_2022_DIRECTORY}/qapnts.dat"
   AND EXISTS "${P7_QA_2022_DIRECTORY}/qarecg.dat")
  add_executable(cteas_p7_original_met_grid_tests tests/p7_original_met_grid_tests.cpp)
  target_link_libraries(cteas_p7_original_met_grid_tests PRIVATE
    cteas_p7_transport cteas_p7_receptors cteas_p7_calmet21)
  if(MSVC)
    target_compile_options(cteas_p7_original_met_grid_tests PRIVATE /W4 /WX)
  else()
    target_compile_options(cteas_p7_original_met_grid_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
  endif()
  add_test(NAME cteas_p7_original_2022_met_header_grid_qa
    COMMAND cteas_p7_original_met_grid_tests
      "${P7_ORIGINAL_GRID_DIR}/grid.cmn"
      "${P7F_LOCKED_CASE_CONTROL}"
      "${P7G_LOCKED_CASE_MET}"
      "${P7_QA_2022_DIRECTORY}/qapnts.dat"
      "${P7_QA_2022_DIRECTORY}/qarecg.dat")
endif()

# Original Fortran storage-kind contract: common-block default REAL*4,
# explicitly typed DOUBLE PRECISION / REAL*8, and default INTEGER*4.
# Runtime code still uses DOUBLE only when the original declares it; a
# double-valued test/probe transport interface is not proof of vendor precision.
add_executable(cteas_p7_precision_contract_tests tests/original_precision_contract_tests.cpp)
target_include_directories(cteas_p7_precision_contract_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)
if(MSVC)
  target_compile_options(cteas_p7_precision_contract_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_precision_contract_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME cteas_p7_original_fortran_cpp_precision_contract
  COMMAND cteas_p7_precision_contract_tests)

# Source-anchored COMP substep order and original 2022 DGM initial state.
# These checks do NOT constitute an integrated CALPUFF execution driver.
add_executable(cteas_p7_vendor_order_tests tests/vendor_order_tests.cpp)
target_include_directories(cteas_p7_vendor_order_tests PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/include")
if(MSVC)
  target_compile_options(cteas_p7_vendor_order_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_vendor_order_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME cteas_p7_vendor_substep_order_contract COMMAND cteas_p7_vendor_order_tests)

set(P7_DGM_HOUR0 "${CMAKE_CURRENT_SOURCE_DIR}/reference/dgm_p7_advection_2022/dgm_puffstep_hour202200100.bin")
set(P7_DGM_META "${CMAKE_CURRENT_SOURCE_DIR}/reference/dgm_p7_advection_2022/dgm_puffstep.json")
set(P7_DGM_AUDIT "${CMAKE_CURRENT_SOURCE_DIR}/reference/dgm_p7_advection_2022/dgm-audit.json")
set(P7_DGM_TOOL "${CMAKE_CURRENT_SOURCE_DIR}/reference/dgm_p7_advection_2022/original_puff_step_dump.py")
set(P7_VENDOR_SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/../../../engine/vendor/src/CALPUFF_v7.2.1_L150618/calpuff.for")
if(EXISTS "${P7_DGM_HOUR0}" AND EXISTS "${P7_DGM_META}" AND EXISTS "${P7_DGM_AUDIT}"
   AND EXISTS "${P7_DGM_TOOL}" AND EXISTS "${P7_VENDOR_SOURCE}"
   AND EXISTS "${P7F_LOCKED_CASE_CONTROL}")
  add_executable(cteas_p7_initial_dgm_tests tests/initial_dgm_oracle_tests.cpp)
  target_link_libraries(cteas_p7_initial_dgm_tests PRIVATE cteas_p7_release cteas_p7_control)
  if(MSVC)
    target_compile_options(cteas_p7_initial_dgm_tests PRIVATE /W4 /WX)
  else()
    target_compile_options(cteas_p7_initial_dgm_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
  endif()
  add_test(NAME cteas_p7_original_initial_internal_xy
    COMMAND cteas_p7_initial_dgm_tests "${P7F_LOCKED_CASE_CONTROL}" "${P7_DGM_HOUR0}")
  add_test(NAME cteas_p7_original_source_dgm_execution_order
    COMMAND "${Python3_EXECUTABLE}"
      "${CMAKE_CURRENT_SOURCE_DIR}/reference/audit_vendor_order_and_dgm.py"
      --vendor "${P7_VENDOR_SOURCE}" --dgm-tool "${P7_DGM_TOOL}"
      --metadata "${P7_DGM_META}" --first-hour "${P7_DGM_HOUR0}"
      --control "${P7F_LOCKED_CASE_CONTROL}" --audit-record "${P7_DGM_AUDIT}")
endif()

# Original DGM first-hour stepping is oracle-FED: physical UADV/WS, old puff
# coordinate and final TSAMP are captured from Fortran; this is NOT a full
# C++ self-propagating puff simulation.
if(EXISTS "${P7_DGM_HOUR0}" AND EXISTS "${P7F_LOCKED_CASE_CONTROL}")
  add_executable(cteas_p7_first_hour_advance_tests tests/dgm_first_hour_advance_tests.cpp)
  target_link_libraries(cteas_p7_first_hour_advance_tests PRIVATE
    cteas_p7_step_integration cteas_p7_control)
  if(MSVC)
    target_compile_options(cteas_p7_first_hour_advance_tests PRIVATE /W4 /WX)
  else()
    target_compile_options(cteas_p7_first_hour_advance_tests PRIVATE
      -Wall -Wextra -Wpedantic -Werror)
  endif()
  add_test(NAME cteas_p7_original_first_hour_advance_real4
    COMMAND cteas_p7_first_hour_advance_tests
      "${P7F_LOCKED_CASE_CONTROL}" "${P7_DGM_HOUR0}")
endif()

# Original 143h WROUT1 structure / PG AVET=PGTIME evidence, not C++ output parity.
set(P7_ORIGINAL_CON_FILE "${CMAKE_CURRENT_SOURCE_DIR}/../../../project/cases/hefei5km_2022_reference_case_20261011/run/puff/puff.con")
if(EXISTS "${P7_ORIGINAL_CON_FILE}" AND EXISTS "${P7F_LOCKED_CASE_CONTROL}")
  add_test(NAME cteas_p7_original_wrout1_header_avefactor_audit
    COMMAND "${Python3_EXECUTABLE}"
      "${CMAKE_CURRENT_SOURCE_DIR}/reference/audit_vendor_wrout1_output.py"
      --control "${P7F_LOCKED_CASE_CONTROL}"
      --original-con "${P7_ORIGINAL_CON_FILE}")
endif()

# Non-prototype native COMP position+SETPUF state-bearing slice. Unlike the
# earlier oracle-fed 1275 independent calls, state is retained and passed
# from one substep to the next for each contiguous puff episode.
add_library(cteas_p7_original_motion STATIC src/original_motion_lifecycle.cpp)
target_include_directories(cteas_p7_original_motion PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}/include")
target_link_libraries(cteas_p7_original_motion PUBLIC cteas_p7_step
  cteas_p7_step_integration cteas_p7_release)
if(MSVC)
  target_compile_options(cteas_p7_original_motion PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_original_motion PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
if(EXISTS "${P7_DGM_HOUR0}" AND EXISTS "${P7F_LOCKED_CASE_CONTROL}")
  add_executable(cteas_p7_first_hour_lifecycle_tests
    tests/dgm_first_hour_lifecycle_tests.cpp)
  target_link_libraries(cteas_p7_first_hour_lifecycle_tests PRIVATE
    cteas_p7_original_motion cteas_p7_control)
  if(MSVC)
    target_compile_options(cteas_p7_first_hour_lifecycle_tests PRIVATE /W4 /WX)
  else()
    target_compile_options(cteas_p7_first_hour_lifecycle_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
  endif()
  add_test(NAME cteas_p7_first_hour_state_persistence_real4
    COMMAND cteas_p7_first_hour_lifecycle_tests
      "${P7F_LOCKED_CASE_CONTROL}" "${P7_DGM_HOUR0}")
endif()

# The original 6h DGM is not checked into the source tree. The controlled
# vendor-only CI regeneration first verifies the full 143h DGM SHA, then writes
# this 11458-record slice and ONLY THEN configures CMake. Missing data can
# never be accepted as a six-hour original-state comparison.
set(P7_DGM_FIRST_6H
  "${CMAKE_CURRENT_SOURCE_DIR}/reference/dgm_p7_advection_2022/dgm_first_six_hours.bin")
if(EXISTS "${P7_DGM_FIRST_6H}" AND EXISTS "${P7F_LOCKED_CASE_CONTROL}")
  add_test(NAME cteas_p7_first_six_hour_state_persistence_real4
    COMMAND cteas_p7_first_hour_lifecycle_tests
      "${P7F_LOCKED_CASE_CONTROL}" "${P7_DGM_FIRST_6H}" 6)
endif()

# A full 143h original DGM is regenerated on the runner (not committed).
# This checks independently initialized *hourwise* real4 motion state, NOT
# autonomous across-hour SWAP/ROLLDN, RISEWIND or puff.con concentration.
set(P7_DGM_FULL_143H
  "${CMAKE_CURRENT_SOURCE_DIR}/reference/dgm_p7_advection_2022/dgm_full_143hours.bin")
if(EXISTS "${P7_DGM_FULL_143H}" AND EXISTS "${P7F_LOCKED_CASE_CONTROL}")
  add_test(NAME cteas_p7_143_hour_oracle_fed_motion_state_real4
    COMMAND cteas_p7_first_hour_lifecycle_tests
      "${P7F_LOCKED_CASE_CONTROL}" "${P7_DGM_FULL_143H}" 143)
endif()

# P7 original METFM=1 physical bridge (GETCELL grid + ADVWND wind), isolated
# from the previous double/absolute-UTM P7C prototype.
add_library(cteas_p7_original_met_cell STATIC src/original_met_cell.cpp)
target_include_directories(cteas_p7_original_met_cell PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(cteas_p7_original_met_cell PUBLIC
  cteas_p7_calmet21 cteas_p7_advection cteas_p7_step_integration)
if(MSVC)
  target_compile_options(cteas_p7_original_met_cell PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_original_met_cell PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_executable(cteas_p7_original_met_cell_trace tests/original_met_cell_trace.cpp)
target_link_libraries(cteas_p7_original_met_cell_trace PRIVATE cteas_p7_original_met_cell)
if(EXISTS "${P7G_LOCKED_CASE_MET}")
  add_test(NAME cteas_p7_original_met_cell_advection_first_hour
    COMMAND cteas_p7_original_met_cell_trace
      "${P7G_LOCKED_CASE_MET}"
      "${CMAKE_CURRENT_SOURCE_DIR}/reference/dgm_p7_advection_2022/dgm_puffstep_hour202200100.bin")
endif()

# P7V original PUFFDZ state integration: previous SIGZ oracle-fed, but the
# determinate Gaussian ZTOP/ZBOT calculation is purely native REAL4.
add_executable(cteas_p7_puffdz_state_trace tests/puffdz_state_trace.cpp)
target_link_libraries(cteas_p7_puffdz_state_trace PRIVATE cteas_p7_advection)
if(MSVC)
  target_compile_options(cteas_p7_puffdz_state_trace PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_puffdz_state_trace PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME cteas_p7_native_puffdz_first_hour
  COMMAND cteas_p7_puffdz_state_trace
    "${CMAKE_CURRENT_SOURCE_DIR}/reference/dgm_p7_advection_2022/dgm_puffstep_hour202200100.bin" 1)

# A production, per-puff REAL4 vertical state connection: native POINTS1/INJECT
# -> persistent SIGZ/ZIOLD/ZIMAX -> PUFFDZ -> METFM1 ADVECT -> P7Q SIGTY/SIGTZ.
# History-dependent ZI evolution remains explicitly unimplemented.
add_library(cteas_p7_original_vertical STATIC src/original_vertical_lifecycle.cpp)
target_include_directories(cteas_p7_original_vertical PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(cteas_p7_original_vertical PUBLIC
  cteas_p7_release cteas_p7_sigma_update cteas_p7_original_met_cell
  cteas_p7_vmass)
if(MSVC)
  target_compile_options(cteas_p7_original_vertical PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_original_vertical PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_executable(cteas_p7_native_vertical_tests tests/native_vertical_lifecycle_tests.cpp)
target_link_libraries(cteas_p7_native_vertical_tests PRIVATE cteas_p7_original_vertical)
if(MSVC)
  target_compile_options(cteas_p7_native_vertical_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_native_vertical_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME cteas_p7_native_vertical_released_persistent_real4
         COMMAND cteas_p7_native_vertical_tests)
if(EXISTS "${P7G_LOCKED_CASE_MET}" AND EXISTS "${P7_DGM_HOUR0}")
  add_test(NAME cteas_p7_native_vertical_original_first_step_real4
    COMMAND cteas_p7_native_vertical_tests
      "${P7G_LOCKED_CASE_MET}" "${P7_DGM_HOUR0}")
endif()

# Vendor VMASS L11667-11950 native REAL*4 vertical mass redistribution.
add_library(cteas_p7_vmass STATIC src/original_vmass.cpp)
target_include_directories(cteas_p7_vmass PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
if(MSVC)
  target_compile_options(cteas_p7_vmass PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_vmass PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_executable(cteas_p7_vmass_tests tests/original_vmass_tests.cpp)
target_link_libraries(cteas_p7_vmass_tests PRIVATE cteas_p7_vmass)
add_test(NAME cteas_p7_native_vmass_source_branch_mass_contract
         COMMAND cteas_p7_vmass_tests)

# Genuine numerical parity against an unmodified extracted vendor VMASS.
# The original Fortran source and *.puf declarations are required; never
# substitute an independently retyped Fortran formula.
add_executable(cteas_p7_vmass_probe src/original_vmass_probe.cpp)
target_link_libraries(cteas_p7_vmass_probe PRIVATE cteas_p7_vmass)

# The first native continuous COMP controller: one *rise-neutral* point puff.
# It is a genuine producer of persistent state, not a DGM replay. Original
# 143h 2022 Hefei source is NOT rise-neutral and remains unaccepted.
add_library(cteas_p7_original_comp_neutral STATIC src/original_comp_neutral.cpp)
target_include_directories(cteas_p7_original_comp_neutral PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(cteas_p7_original_comp_neutral PUBLIC
  cteas_p7_original_vertical cteas_p7_original_motion
  cteas_p7_step_integration cteas_p7_step cteas_p7_dispersion)
if(MSVC)
  target_compile_options(cteas_p7_original_comp_neutral PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_original_comp_neutral PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_executable(cteas_p7_original_comp_neutral_tests tests/original_comp_neutral_tests.cpp)
target_link_libraries(cteas_p7_original_comp_neutral_tests PRIVATE cteas_p7_original_comp_neutral)
if(MSVC)
  target_compile_options(cteas_p7_original_comp_neutral_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_original_comp_neutral_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
foreach(HOURS IN ITEMS 1 6 143)
  add_test(NAME cteas_p7_native_comp_neutral_${HOURS}h_persistent
           COMMAND cteas_p7_original_comp_neutral_tests ${HOURS})
endforeach()

# MDISP=3 live SIGTY/SIGTZ coupled to native METFM1 within one COMP step.
add_test(NAME cteas_p7_native_comp_neutral_pg_1h_persistent
         COMMAND cteas_p7_original_comp_neutral_tests pg)
add_test(NAME cteas_p7_native_comp_neutral_pg_6h_persistent
         COMMAND cteas_p7_original_comp_neutral_tests pg6)
add_test(NAME cteas_p7_native_comp_neutral_pg_143h_persistent
         COMMAND cteas_p7_original_comp_neutral_tests pg143)

# Native REAL4 bridge from the original METFM1 column through GRISE and
# RISEWIND. The caller must supply true independently calculated native
# PRFIN/PUFFDZ state; this is not an autonomous 143-hour production solver.
add_library(cteas_p7_original_rise_met STATIC src/original_rise_met.cpp)
target_include_directories(cteas_p7_original_rise_met PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(cteas_p7_original_rise_met PUBLIC
  cteas_p7_original_met_cell cteas_p7_rise_wind cteas_p7_plume_rise)
if(MSVC)
  target_compile_options(cteas_p7_original_rise_met PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_original_rise_met PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_executable(cteas_p7_original_rise_met_tests tests/original_rise_met_tests.cpp)
target_link_libraries(cteas_p7_original_rise_met_tests PRIVATE cteas_p7_original_rise_met)
if(MSVC)
  target_compile_options(cteas_p7_original_rise_met_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_original_rise_met_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME cteas_p7_native_metfm1_grise_risewind
  COMMAND cteas_p7_original_rise_met_tests)

# A deterministic, transactional native COMP *hour* over multiple puffs.
# The tested fixture uses caller admissions, not original POINTS1/SWAP.
add_library(cteas_p7_original_comp_hourly STATIC src/original_comp_hourly.cpp)
target_include_directories(cteas_p7_original_comp_hourly PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(cteas_p7_original_comp_hourly PUBLIC cteas_p7_original_comp_neutral)
if(MSVC)
  target_compile_options(cteas_p7_original_comp_hourly PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_original_comp_hourly PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_executable(cteas_p7_original_comp_hourly_tests tests/original_comp_hourly_tests.cpp)
target_link_libraries(cteas_p7_original_comp_hourly_tests PRIVATE cteas_p7_original_comp_hourly)
if(MSVC)
  target_compile_options(cteas_p7_original_comp_hourly_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_original_comp_hourly_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
foreach(HOURS IN ITEMS 1 6 143)
  add_test(NAME cteas_p7_native_comp_pg_multipuff_${HOURS}h
           COMMAND cteas_p7_original_comp_hourly_tests ${HOURS})
endforeach()

# Source CALPUFF COMP L10629-10649 / METFM1 WDIV L9555-9566,
# independently opt-in (never changed for historical non-WDIV regression).
add_library(cteas_p7_original_vertical_divergence STATIC src/original_vertical_divergence.cpp)
target_include_directories(cteas_p7_original_vertical_divergence PUBLIC
  ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(cteas_p7_original_vertical_divergence PUBLIC
  cteas_p7_advection cteas_p7_calmet21 cteas_p7_original_met_cell)
if(MSVC)
  target_compile_options(cteas_p7_original_vertical_divergence PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_original_vertical_divergence PRIVATE
    -Wall -Wextra -Wpedantic -Werror)
endif()

# Native restricted *rising* point puff chain: METFM1 -> PUFFDZ -> 
# GRISE/RISEWIND -> location -> REAL4 PG SIGTY/SIGTZ -> VMASS/COMP.
add_library(cteas_p7_original_comp_rise STATIC src/original_comp_rise.cpp)
target_include_directories(cteas_p7_original_comp_rise PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(cteas_p7_original_comp_rise PUBLIC
  cteas_p7_original_vertical cteas_p7_original_motion
  cteas_p7_original_rise_met cteas_p7_step_integration
  cteas_p7_step cteas_p7_dispersion
  cteas_p7_dry_deposition cteas_p7_coupling
  cteas_p7_original_vertical_divergence)
if(MSVC)
  target_compile_options(cteas_p7_original_comp_rise PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_original_comp_rise PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_executable(cteas_p7_original_comp_rise_tests tests/original_comp_rise_tests.cpp)
target_link_libraries(cteas_p7_original_comp_rise_tests PRIVATE cteas_p7_original_comp_rise)
if(MSVC)
  target_compile_options(cteas_p7_original_comp_rise_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_original_comp_rise_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
foreach(HOURS IN ITEMS 1 6 143)
  add_test(NAME cteas_p7_native_rise_comp_pg_${HOURS}h
           COMMAND cteas_p7_original_comp_rise_tests ${HOURS})
endforeach()

# Native multi-point puff GRISE + RISEWIND + PG COMP whole-hour transaction;
# frozen Hefei numerical parity and original POINTS1 cadence remain OPEN.
add_library(cteas_p7_original_comp_rise_hourly STATIC src/original_comp_rise_hourly.cpp)
target_include_directories(cteas_p7_original_comp_rise_hourly PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(cteas_p7_original_comp_rise_hourly PUBLIC cteas_p7_original_comp_rise)
if(MSVC)
  target_compile_options(cteas_p7_original_comp_rise_hourly PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_original_comp_rise_hourly PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_executable(cteas_p7_original_comp_rise_hourly_tests tests/original_comp_rise_hourly_tests.cpp)
target_link_libraries(cteas_p7_original_comp_rise_hourly_tests PRIVATE cteas_p7_original_comp_rise_hourly)
if(MSVC)
  target_compile_options(cteas_p7_original_comp_rise_hourly_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_original_comp_rise_hourly_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
foreach(HOURS IN ITEMS 1 6 143)
  add_test(NAME cteas_p7_native_rise_comp_pg_multipuff_${HOURS}h
           COMMAND cteas_p7_original_comp_rise_hourly_tests ${HOURS})
endforeach()

# Native POINTS1 cadence applied to existing rising-puff hourly scheduler.
# Real RLSMET WSNEW still requires independently source-ported input.
add_executable(cteas_p7_original_point_hourly_cadence_tests tests/original_point_hourly_cadence_tests.cpp)
target_link_libraries(cteas_p7_original_point_hourly_cadence_tests PRIVATE cteas_p7_original_comp_rise_hourly)
if(MSVC)
  target_compile_options(cteas_p7_original_point_hourly_cadence_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_original_point_hourly_cadence_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
foreach(HOURS IN ITEMS 1 6 143)
  add_test(NAME cteas_p7_point_hourly_cadence_${HOURS}h
           COMMAND cteas_p7_original_point_hourly_cadence_tests ${HOURS})
endforeach()

# Source-pinned RLSMET -> WINDSET: selected METFM1 release WSNEW only.
# Original full RLSMET PTLAPS/dispersion/PRFIN still independent.
add_library(cteas_p7_original_release_wind STATIC src/original_release_wind.cpp)
target_include_directories(cteas_p7_original_release_wind PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(cteas_p7_original_release_wind PUBLIC
  cteas_p7_original_met_cell cteas_p7_release cteas_p7_calmet21)
if(MSVC)
  target_compile_options(cteas_p7_original_release_wind PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_original_release_wind PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
# Reusable source-ordered point PRFIN/PRFPP/WSNEW bridge, independent of
# test fixtures, original DGM initial states and case-specific coordinates.
add_library(cteas_p7_original_point_prfin STATIC src/original_point_prfin.cpp)
target_include_directories(cteas_p7_original_point_prfin PUBLIC
  ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(cteas_p7_original_point_prfin PUBLIC
  cteas_p7_original_release_wind cteas_p7_plume_rise cteas_p7_release)
if(MSVC)
  target_compile_options(cteas_p7_original_point_prfin PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_original_point_prfin PRIVATE
    -Wall -Wextra -Wpedantic -Werror)
endif()
add_executable(cteas_p7_original_release_wind_tests tests/original_release_wind_tests.cpp)
target_link_libraries(cteas_p7_original_release_wind_tests PRIVATE cteas_p7_original_release_wind)
if(MSVC)
  target_compile_options(cteas_p7_original_release_wind_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_original_release_wind_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME cteas_p7_native_windset_release_synthetic
         COMMAND cteas_p7_original_release_wind_tests)
set(P7_RLSMET_REAL_DGM "${CMAKE_CURRENT_SOURCE_DIR}/reference/dgm_p7_advection_2022/dgm_puffstep_hour202200100.bin")
if(EXISTS "${P7G_LOCKED_CASE_MET}" AND EXISTS "${P7_RLSMET_REAL_DGM}")
  add_test(NAME cteas_p7_native_windset_rlsmet_2022_first_hour
           COMMAND cteas_p7_original_release_wind_tests
           "${P7G_LOCKED_CASE_MET}" "${P7_RLSMET_REAL_DGM}")
endif()

# Native selection of WSNEW from original WINDSET at PRFIN effective height
# instead of externally supplied source.cadence.wind_speed_ms.
target_link_libraries(cteas_p7_original_comp_rise_hourly PUBLIC cteas_p7_original_release_wind)
add_test(NAME cteas_p7_point_hourly_cadence_native_rlsmet
         COMMAND cteas_p7_original_point_hourly_cadence_tests rlsmet)

# Strict original 2022 COMP NEW-puff cadence comparison, REAL4.
# Old-puff NSAM needs the original pre-RISEWIND wind (not DGM postwind WS).
add_executable(cteas_p7_original_comp_cadence_trace
  tests/original_comp_cadence_trace.cpp)
target_link_libraries(cteas_p7_original_comp_cadence_trace PRIVATE
  cteas_p7_step_integration cteas_p7_release)
if(MSVC)
  target_compile_options(cteas_p7_original_comp_cadence_trace PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_original_comp_cadence_trace PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME cteas_p7_comp_new_cadence_original_first_hour
  COMMAND cteas_p7_original_comp_cadence_trace "${P7_DGM_HOUR0}" 1)
if(EXISTS "${P7_DGM_FULL_143H}")
  add_test(NAME cteas_p7_comp_new_cadence_original_143h
    COMMAND cteas_p7_original_comp_cadence_trace "${P7_DGM_FULL_143H}" 143)
endif()

# Original CALPUFF DGM is read only: native controller must reconstruct
# every FSTEP/TSAMP/TLEFT and label-500 same-KSAM reentry from the original
# measured pre-FSTEP WS, NSAM and REFTSAMP, never from original TSAMP.
add_executable(cteas_p7_original_fstep_trace tests/original_comp_fstep_trace.cpp)
target_link_libraries(cteas_p7_original_fstep_trace PRIVATE cteas_p7_step_integration)
if(MSVC)
  target_compile_options(cteas_p7_original_fstep_trace PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_original_fstep_trace PRIVATE
    -Wall -Wextra -Wpedantic -Werror)
endif()
if(EXISTS "${P7_DGM_HOUR0}")
  add_test(NAME cteas_p7_original_first_hour_fstep_controller
    COMMAND cteas_p7_original_fstep_trace "${P7_DGM_HOUR0}" 1)
endif()
if(EXISTS "${P7_DGM_FIRST_6H}")
  add_test(NAME cteas_p7_original_six_hour_fstep_controller
    COMMAND cteas_p7_original_fstep_trace "${P7_DGM_FIRST_6H}" 6)
endif()
if(EXISTS "${P7_DGM_FULL_143H}")
  add_test(NAME cteas_p7_original_143_hour_fstep_controller
    COMMAND cteas_p7_original_fstep_trace "${P7_DGM_FULL_143H}" 143)
endif()

# Vendor COMP early QALL retirement (L10450) and post-step puff-center
# domain exit (L11400). CALPUFF original XB/XE/YB/YE supplied by caller.
add_library(cteas_p7_original_comp_exit STATIC src/original_comp_exit.cpp)
target_include_directories(cteas_p7_original_comp_exit PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
if(MSVC)
  target_compile_options(cteas_p7_original_comp_exit PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_original_comp_exit PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
target_link_libraries(cteas_p7_original_comp_rise_hourly PUBLIC cteas_p7_original_comp_exit)
add_executable(cteas_p7_original_comp_exit_tests tests/original_comp_exit_tests.cpp)
target_link_libraries(cteas_p7_original_comp_exit_tests PRIVATE cteas_p7_original_comp_exit)
if(MSVC)
  target_compile_options(cteas_p7_original_comp_exit_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_original_comp_exit_tests PRIVATE
    -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME cteas_p7_original_comp_exit_source_contract
  COMMAND cteas_p7_original_comp_exit_tests)

# Selected REAL4 COMP old/new MXSAM=99 outer-hour execution and native
# METFM1/GRISE/RISEWIND/PG/VMASS inner substeps, no FSTEP dynamic split.
add_executable(cteas_p7_original_comp_mxsam99_unsplit_tests
  tests/original_comp_mxsam99_unsplit_tests.cpp)
# Source-ported original PUFRECS receptor projection and FCLIP front-end.
add_library(cteas_p7_original_pufrecs_geometry STATIC src/original_pufrecs_geometry.cpp)
target_include_directories(cteas_p7_original_pufrecs_geometry PUBLIC
  ${CMAKE_CURRENT_SOURCE_DIR}/include)
add_executable(cteas_p7_original_pufrecs_geometry_tests
  tests/original_pufrecs_geometry_tests.cpp)
add_executable(cteas_p7_original_pufrecs_geometry_probe
  src/original_pufrecs_geometry_probe.cpp)
target_link_libraries(cteas_p7_original_pufrecs_geometry_probe PRIVATE
  cteas_p7_original_pufrecs_geometry)

target_link_libraries(cteas_p7_original_pufrecs_geometry_tests PRIVATE
  cteas_p7_original_pufrecs_geometry)
if(MSVC)
  target_compile_options(cteas_p7_original_pufrecs_geometry PRIVATE /W4 /WX)
  target_compile_options(cteas_p7_original_pufrecs_geometry_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_original_pufrecs_geometry PRIVATE
    -Wall -Wextra -Wpedantic -Werror)
  target_compile_options(cteas_p7_original_pufrecs_geometry_tests PRIVATE
    -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME cteas_p7_original_pufrecs_geometry
  COMMAND cteas_p7_original_pufrecs_geometry_tests)

# Original CALPUFF PUFFCT2 receptor height for MCTADJ=2.
# Pure port: CTADJ2/SETPUF still must supply native FRACZ1 and LUP1.
add_library(cteas_p7_original_puffct2 STATIC src/original_puffct2.cpp)
target_include_directories(cteas_p7_original_puffct2 PUBLIC
  ${CMAKE_CURRENT_SOURCE_DIR}/include)
add_executable(cteas_p7_original_puffct2_probe
  src/original_puffct2_probe.cpp)
target_link_libraries(cteas_p7_original_puffct2_probe PRIVATE
  cteas_p7_original_puffct2)
add_executable(cteas_p7_original_puffct2_tests
  tests/original_puffct2_tests.cpp)
target_link_libraries(cteas_p7_original_puffct2_tests PRIVATE
  cteas_p7_original_puffct2)
if(MSVC)
  target_compile_options(cteas_p7_original_puffct2 PRIVATE /W4 /WX)
  target_compile_options(cteas_p7_original_puffct2_probe PRIVATE /W4 /WX)
  target_compile_options(cteas_p7_original_puffct2_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_original_puffct2 PRIVATE -Wall -Wextra -Wpedantic -Werror)
  target_compile_options(cteas_p7_original_puffct2_probe PRIVATE -Wall -Wextra -Wpedantic -Werror)
  target_compile_options(cteas_p7_original_puffct2_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME cteas_p7_original_puffct2_source_contract
  COMMAND cteas_p7_original_puffct2_tests)

# Original CALMET.DAT OUTHD ELEV -> source-ported GETELEV/TRELIEF/VWIDTH
# adapter for the selected MCTADJ2 point-receptor terrain path.
add_library(cteas_p7_original_native_terrain STATIC
  src/original_native_terrain.cpp)
target_include_directories(cteas_p7_original_native_terrain PUBLIC
  ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(cteas_p7_original_native_terrain PUBLIC
  cteas_p7_terrain_state cteas_p7_valley_width cteas_p7_step_integration)
add_executable(cteas_p7_original_native_terrain_tests
  tests/original_native_terrain_tests.cpp)
target_link_libraries(cteas_p7_original_native_terrain_tests PRIVATE
  cteas_p7_original_native_terrain)
if(MSVC)
  target_compile_options(cteas_p7_original_native_terrain PRIVATE /W4 /WX)
  target_compile_options(cteas_p7_original_native_terrain_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_original_native_terrain PRIVATE
    -Wall -Wextra -Wpedantic -Werror)
  target_compile_options(cteas_p7_original_native_terrain_tests PRIVATE
    -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME cteas_p7_original_native_terrain_real_input_adapter
  COMMAND cteas_p7_original_native_terrain_tests)
# Genuine frozen 2022 CALMET.DAT terrain input and provenance; this
# deliberately does NOT claim real-case CTADJ2→CALCPF scientific parity.
add_executable(cteas_p7_original_native_terrain_frozen_met_tests
  tests/original_native_terrain_frozen_met_tests.cpp)
target_link_libraries(cteas_p7_original_native_terrain_frozen_met_tests PRIVATE
  cteas_p7_original_native_terrain cteas_p7_calmet21)
if(MSVC)
  target_compile_options(cteas_p7_original_native_terrain_frozen_met_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_original_native_terrain_frozen_met_tests PRIVATE
    -Wall -Wextra -Wpedantic -Werror)
endif()
if(EXISTS "${P7G_LOCKED_CASE_MET}")
  add_test(NAME cteas_p7_hefei_frozen_met_terrain_source
    COMMAND cteas_p7_original_native_terrain_frozen_met_tests
      "${P7G_LOCKED_CASE_MET}")
endif()

# Selected genuine Hefei 2022 Group 13b stack -> original 143h METFM1
# WINDSET at HTSTAK, no DGM driving input and no PRFIN/parity claim.
add_executable(cteas_p7_original_hefei_source_met_bridge_tests
  tests/original_hefei_source_met_bridge_tests.cpp)
target_link_libraries(cteas_p7_original_hefei_source_met_bridge_tests PRIVATE
  cteas_p7_original_release_wind cteas_p7_calmet21
  cteas_p7_plume_rise cteas_p7_control cteas_p7_release
  cteas_p7_original_point_prfin)
if(MSVC)
  target_compile_options(cteas_p7_original_hefei_source_met_bridge_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_original_hefei_source_met_bridge_tests PRIVATE
    -Wall -Wextra -Wpedantic -Werror)
endif()
set(P7_HEFEI_POINT_INP
  "${CMAKE_CURRENT_SOURCE_DIR}/../../../project/cases/hefei5km_2022_reference_case_20261011/run/puff/puff.inp")
if(EXISTS "${P7G_LOCKED_CASE_MET}" AND EXISTS "${P7_HEFEI_POINT_INP}")
  add_test(NAME cteas_p7_hefei_source_met_stack_bridge
    COMMAND cteas_p7_original_hefei_source_met_bridge_tests
      "${P7G_LOCKED_CASE_MET}" "${P7_HEFEI_POINT_INP}")
endif()

# Genuine first-hour POINTS1 54 native admission and earliest physical
# COMP divergence. DGM is an immutable comparator, never a solver input.
add_executable(cteas_p7_hefei_firsthour_native_comp_tests
  tests/original_hefei_firsthour_native_comp_tests.cpp)
target_link_libraries(cteas_p7_hefei_firsthour_native_comp_tests PRIVATE
  cteas_p7_original_comp_rise_hourly cteas_p7_original_point_prfin
  cteas_p7_calmet21 cteas_p7_control
  cteas_p7_original_native_terrain)
if(MSVC)
  target_compile_options(cteas_p7_hefei_firsthour_native_comp_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_hefei_firsthour_native_comp_tests PRIVATE
    -Wall -Wextra -Wpedantic -Werror)
endif()
set(P7_HEFEI_FIRSTHOUR_DGM
  "${CMAKE_CURRENT_SOURCE_DIR}/reference/dgm_p7_advection_2022/dgm_puffstep_hour202200100.bin")
if(EXISTS "${P7G_LOCKED_CASE_MET}" AND EXISTS "${P7_HEFEI_POINT_INP}" AND
   EXISTS "${P7_HEFEI_FIRSTHOUR_DGM}")
  add_test(NAME cteas_p7_hefei_real_54_puff_native_admissions
    COMMAND cteas_p7_hefei_firsthour_native_comp_tests
      "${P7G_LOCKED_CASE_MET}" "${P7_HEFEI_POINT_INP}"
      "${P7_HEFEI_FIRSTHOUR_DGM}")
endif()

# Frozen Hefei 2022 native full first-hour (1275 COMP substeps) H-3-only
# receptor integration with genuine MCTADJ2/PTLAPS, MDRY=1 and original
# puff.con as read-only diagnostic; scientific concentration parity is OPEN.
add_executable(cteas_p7_hefei_firsthour_native_h3_receptors_tests
  tests/original_hefei_firsthour_native_receptors_tests.cpp)
target_link_libraries(cteas_p7_hefei_firsthour_native_h3_receptors_tests PRIVATE
  cteas_p7_original_comp_rise_hourly cteas_p7_original_point_prfin
  cteas_p7_calmet21 cteas_p7_control
  cteas_p7_original_native_terrain cteas_p7_original_flat_calcpf
  cteas_p7_receptors cteas_p7_dry_deposition)
if(MSVC)
  target_compile_options(cteas_p7_hefei_firsthour_native_h3_receptors_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_hefei_firsthour_native_h3_receptors_tests PRIVATE
    -Wall -Wextra -Wpedantic -Werror)
endif()
set(P7_HEFEI_REFERENCE_CON
  "${CMAKE_CURRENT_SOURCE_DIR}/../../../project/cases/hefei5km_2022_reference_case_20261011/run/puff/puff.con")
if(EXISTS "${P7G_LOCKED_CASE_MET}" AND EXISTS "${P7_HEFEI_POINT_INP}"
   AND EXISTS "${P7_HEFEI_REFERENCE_CON}")
  add_test(NAME cteas_p7_hefei_real_firsthour_h3_receptor_diagnostic
    COMMAND cteas_p7_hefei_firsthour_native_h3_receptors_tests
      "${P7G_LOCKED_CASE_MET}" "${P7_HEFEI_POINT_INP}" "${P7_HEFEI_REFERENCE_CON}")
endif()

# Frozen Hefei 2022 real six-hour contiguous COMP/PFSAMP/CALCPF ledger.
# A diagnostic PASS never automatically implies 6h science acceptance;
# strict first-hour H-3 bitwise parity remains mandatory.
add_executable(cteas_p7_hefei_sixhour_native_h3_receptors_tests
  tests/original_hefei_sixhour_native_receptors_tests.cpp)
target_link_libraries(cteas_p7_hefei_sixhour_native_h3_receptors_tests PRIVATE
  cteas_p7_original_comp_rise_hourly cteas_p7_original_point_prfin
  cteas_p7_calmet21 cteas_p7_control
  cteas_p7_original_native_terrain cteas_p7_original_flat_calcpf
  cteas_p7_receptors cteas_p7_dry_deposition)
if(MSVC)
  target_compile_options(cteas_p7_hefei_sixhour_native_h3_receptors_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_hefei_sixhour_native_h3_receptors_tests PRIVATE
    -Wall -Wextra -Wpedantic -Werror)
endif()
if(EXISTS "${P7G_LOCKED_CASE_MET}" AND EXISTS "${P7_HEFEI_POINT_INP}"
   AND EXISTS "${P7_HEFEI_REFERENCE_CON}")
  add_test(NAME cteas_p7_hefei_real_sixhour_comp_precision_diagnostic
    COMMAND cteas_p7_hefei_sixhour_native_h3_receptors_tests
      "${P7G_LOCKED_CASE_MET}" "${P7_HEFEI_POINT_INP}" "${P7_HEFEI_REFERENCE_CON}")
endif()

# S2-2D: genuine standalone Hefei 2022 no-oracle P7 emitter.
# Reuse the identical production physics libraries linked to the validated
# frozen-C1 143h test-driver; the executable source does not accept or open
# original `puff.con`/DGM. Scientific parity remains an INDEPENDENT test.
add_executable(cteas_p7_native_hefei_2022 src/native_hefei_2022_main.cpp)
target_link_libraries(cteas_p7_native_hefei_2022 PRIVATE
  cteas_p7_original_comp_rise_hourly cteas_p7_original_point_prfin
  cteas_p7_calmet21 cteas_p7_control
  cteas_p7_original_native_terrain cteas_p7_original_flat_calcpf
  cteas_p7_receptors cteas_p7_dry_deposition)
if(MSVC)
  target_compile_options(cteas_p7_native_hefei_2022 PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_native_hefei_2022 PRIVATE
    -Wall -Wextra -Wpedantic -Werror)
endif()

# Production native COMP post-rise calm IDOPT=1 opt-in,
# original TURBSET minima, transaction and unsupported branch rollback.
add_executable(cteas_p7_original_comp_calm_integrated_tests
  tests/original_comp_calm_integrated_tests.cpp)
target_link_libraries(cteas_p7_original_comp_calm_integrated_tests PRIVATE
  cteas_p7_original_comp_rise_hourly)
if(MSVC)
  target_compile_options(cteas_p7_original_comp_calm_integrated_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_original_comp_calm_integrated_tests PRIVATE
    -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME cteas_p7_native_comp_calm_idopt1_transaction
  COMMAND cteas_p7_original_comp_calm_integrated_tests)

# Original COMP post-RISEWIND WSCALM=0.5, UCALM=0.001,
# and strict rejection of missing calm IDOPTYS/IDOPTZS=1 dispersion.
# Exercises actual two-hour state/rollback, not only a pure math helper.
add_executable(cteas_p7_original_comp_calm_tests
  tests/original_comp_calm_tests.cpp)
target_link_libraries(cteas_p7_original_comp_calm_tests PRIVATE
  cteas_p7_original_comp_rise_hourly)
if(MSVC)
  target_compile_options(cteas_p7_original_comp_calm_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_original_comp_calm_tests PRIVATE
    -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME cteas_p7_native_comp_calm_branch_atomic
  COMMAND cteas_p7_original_comp_calm_tests)

# Restricted native CALCPF gridded point-source bridge: PFSCRN/PFSAMP/VCOUP.
# This is NOT a replacement for full original receptor-specific PUFRECS.
# Standalone original-vs-native PFSCRN REAL4 bit comparison probe.
add_executable(cteas_p7_original_pfscrn_probe src/original_pfscrn_probe.cpp)
target_link_libraries(cteas_p7_original_pfscrn_probe PRIVATE cteas_p7_receptors)
if(MSVC)
  target_compile_options(cteas_p7_original_pfscrn_probe PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_original_pfscrn_probe PRIVATE
    -Wall -Wextra -Wpedantic -Werror)
endif()
add_library(cteas_p7_original_flat_calcpf STATIC src/original_flat_calcpf.cpp)
target_include_directories(cteas_p7_original_flat_calcpf PUBLIC
  ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(cteas_p7_original_flat_calcpf PUBLIC
  cteas_p7_receptors cteas_p7_dispersion cteas_p7_plume_rise
  cteas_p7_original_pufrecs_geometry cteas_p7_original_puffct2)
if(MSVC)
  target_compile_options(cteas_p7_original_flat_calcpf PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_original_flat_calcpf PRIVATE
    -Wall -Wextra -Wpedantic -Werror)
endif()
target_link_libraries(cteas_p7_original_comp_mxsam99_unsplit_tests PRIVATE
  cteas_p7_original_comp_rise_hourly cteas_p7_receptors
  cteas_p7_original_flat_calcpf cteas_p7_original_pufrecs_geometry
  cteas_p7_original_native_terrain)
if(MSVC)
  target_compile_options(cteas_p7_original_comp_mxsam99_unsplit_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_original_comp_mxsam99_unsplit_tests PRIVATE
    -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME cteas_p7_native_comp_mxsam99_unsplit
         COMMAND cteas_p7_original_comp_mxsam99_unsplit_tests)

# Original Fortran CALPUFF v7.2.1 ROLLDN L19110-19215 slot ordering.
# State itself stays in native motion/rise/vertical stores under episode IDs.
add_library(cteas_p7_original_rolldn STATIC src/original_rolldn.cpp)
target_include_directories(cteas_p7_original_rolldn PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
if(MSVC)
  target_compile_options(cteas_p7_original_rolldn PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_original_rolldn PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
target_link_libraries(cteas_p7_original_comp_rise_hourly PUBLIC cteas_p7_original_rolldn)
add_executable(cteas_p7_original_rolldn_tests tests/original_rolldn_tests.cpp)
target_link_libraries(cteas_p7_original_rolldn_tests PRIVATE cteas_p7_original_rolldn)
if(MSVC)
  target_compile_options(cteas_p7_original_rolldn_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p7_original_rolldn_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME cteas_p7_original_rolldn_slot_order
         COMMAND cteas_p7_original_rolldn_tests)
