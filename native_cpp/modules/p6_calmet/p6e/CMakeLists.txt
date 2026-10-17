cmake_minimum_required(VERSION 3.20)
project(CTEAS_P6E_SOLAR LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
add_library(p6e_solar INTERFACE)
target_include_directories(p6e_solar INTERFACE include)
add_executable(p6e_solar_tests tests/solar_tests.cpp)
add_executable(p6e_solar_reference src/solar_reference_main.cpp)
target_link_libraries(p6e_solar_tests PRIVATE p6e_solar)
target_link_libraries(p6e_solar_reference PRIVATE p6e_solar)
if(MSVC)
 target_compile_options(p6e_solar_tests PRIVATE /W4 /WX)
 target_compile_options(p6e_solar_reference PRIVATE /W4 /WX)
else()
 target_compile_options(p6e_solar_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
 target_compile_options(p6e_solar_reference PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
enable_testing()
add_test(NAME p6e_solar_software COMMAND p6e_solar_tests)

# COORDLIB (GCTP 2.0.2) UTM inverse, ported from the CALMET vendor coordlib.for.
# The software test pins the REAL*4 grid geometry of the frozen 2022 case; the
# parity test re-derives it from the unmodified Fortran source over a wider
# parameter matrix and is registered whenever a gfortran is present.
find_package(Python3 COMPONENTS Interpreter REQUIRED)
add_executable(p6e_coordlib_pj09z0_tests tests/coordlib_pj09z0_tests.cpp)
add_executable(p6e_coordlib_utm_reference src/coordlib_utm_reference_main.cpp)
target_link_libraries(p6e_coordlib_pj09z0_tests PRIVATE p6e_solar)
target_link_libraries(p6e_coordlib_utm_reference PRIVATE p6e_solar)
if(MSVC)
  target_compile_options(p6e_coordlib_pj09z0_tests PRIVATE /W4 /WX)
  target_compile_options(p6e_coordlib_utm_reference PRIVATE /W4 /WX)
else()
  target_compile_options(p6e_coordlib_pj09z0_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
  target_compile_options(p6e_coordlib_utm_reference PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6e_coordlib_pj09z0_software COMMAND p6e_coordlib_pj09z0_tests)

find_program(P6E_GFORTRAN NAMES gfortran-13 gfortran-12 gfortran-11 gfortran)
if(P6E_GFORTRAN)
  add_test(NAME p6e_coordlib_utm_original_source_parity
    COMMAND "${Python3_EXECUTABLE}"
      "${CMAKE_CURRENT_SOURCE_DIR}/reference/compare_original_coordlib_utm.py"
      --vendor "${CMAKE_CURRENT_SOURCE_DIR}/../../../../engine/vendor/src/CALMET_v6.5.0_L150223/coordlib.for"
      --cpp "$<TARGET_FILE:p6e_coordlib_utm_reference>"
      --gfortran "${P6E_GFORTRAN}"
      --out "${CMAKE_CURRENT_BINARY_DIR}/coordlib-utm-original-parity.json")
  message(STATUS "P6E COORDLIB UTM original-source parity test: REGISTERED (${P6E_GFORTRAN})")
else()
  message(STATUS "P6E COORDLIB UTM original-source parity test: not registered (no Fortran compiler)")
endif()

add_executable(p6e_pgtstb_tests tests/pgtstb_tests.cpp)
add_executable(p6e_pgtstb_reference src/pgtstb_reference_main.cpp)
target_link_libraries(p6e_pgtstb_tests PRIVATE p6e_solar)
target_link_libraries(p6e_pgtstb_reference PRIVATE p6e_solar)
if(MSVC)
  target_compile_options(p6e_pgtstb_tests PRIVATE /W4 /WX)
  target_compile_options(p6e_pgtstb_reference PRIVATE /W4 /WX)
else()
  target_compile_options(p6e_pgtstb_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
  target_compile_options(p6e_pgtstb_reference PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6e_pgtstb_software COMMAND p6e_pgtstb_tests)

add_executable(p6e_surfvar_observed_tests tests/surfvar_observed_tests.cpp)
add_executable(p6e_surfvar_observed_reference src/surfvar_observed_reference_main.cpp)
target_link_libraries(p6e_surfvar_observed_tests PRIVATE p6e_solar)
target_link_libraries(p6e_surfvar_observed_reference PRIVATE p6e_solar)
if(MSVC)
  target_compile_options(p6e_surfvar_observed_tests PRIVATE /W4 /WX)
  target_compile_options(p6e_surfvar_observed_reference PRIVATE /W4 /WX)
else()
  target_compile_options(p6e_surfvar_observed_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
  target_compile_options(p6e_surfvar_observed_reference PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6e_surfvar_observed_software COMMAND p6e_surfvar_observed_tests)

add_executable(p6e_heatfx_tests tests/heatfx_tests.cpp)
add_executable(p6e_heatfx_reference src/heatfx_reference_main.cpp)
target_link_libraries(p6e_heatfx_tests PRIVATE p6e_solar)
target_link_libraries(p6e_heatfx_reference PRIVATE p6e_solar)
if(MSVC)
  target_compile_options(p6e_heatfx_tests PRIVATE /W4 /WX)
  target_compile_options(p6e_heatfx_reference PRIVATE /W4 /WX)
else()
  target_compile_options(p6e_heatfx_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
  target_compile_options(p6e_heatfx_reference PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6e_heatfx_software COMMAND p6e_heatfx_tests)

add_executable(p6e_elustr_stable_tests tests/elustr_stable_tests.cpp)
add_executable(p6e_elustr_stable_reference src/elustr_stable_reference_main.cpp)
target_link_libraries(p6e_elustr_stable_tests PRIVATE p6e_solar)
target_link_libraries(p6e_elustr_stable_reference PRIVATE p6e_solar)
if(MSVC)
 target_compile_options(p6e_elustr_stable_tests PRIVATE /W4 /WX)
 target_compile_options(p6e_elustr_stable_reference PRIVATE /W4 /WX)
else()
 target_compile_options(p6e_elustr_stable_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
 target_compile_options(p6e_elustr_stable_reference PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6e_elustr_stable_software COMMAND p6e_elustr_stable_tests)

add_executable(p6e_wstarr_tests tests/wstarr_tests.cpp)
add_executable(p6e_wstarr_reference src/wstarr_reference_main.cpp)
target_link_libraries(p6e_wstarr_tests PRIVATE p6e_solar)
target_link_libraries(p6e_wstarr_reference PRIVATE p6e_solar)
if(MSVC)
 target_compile_options(p6e_wstarr_tests PRIVATE /W4 /WX)
 target_compile_options(p6e_wstarr_reference PRIVATE /W4 /WX)
else()
 target_compile_options(p6e_wstarr_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
 target_compile_options(p6e_wstarr_reference PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6e_wstarr_software COMMAND p6e_wstarr_tests)

add_executable(p6e_mixht_stable_tests tests/mixht_stable_tests.cpp)
add_executable(p6e_mixht_stable_reference src/mixht_stable_reference_main.cpp)
target_link_libraries(p6e_mixht_stable_tests PRIVATE p6e_solar)
target_link_libraries(p6e_mixht_stable_reference PRIVATE p6e_solar)
if(MSVC)
 target_compile_options(p6e_mixht_stable_tests PRIVATE /W4 /WX)
 target_compile_options(p6e_mixht_stable_reference PRIVATE /W4 /WX)
else()
 target_compile_options(p6e_mixht_stable_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
 target_compile_options(p6e_mixht_stable_reference PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6e_mixht_stable_software COMMAND p6e_mixht_stable_tests)

add_executable(p6e_elustr_daytime_tests tests/elustr_daytime_tests.cpp)
add_executable(p6e_elustr_daytime_reference src/elustr_daytime_reference_main.cpp)
target_link_libraries(p6e_elustr_daytime_tests PRIVATE p6e_solar)
target_link_libraries(p6e_elustr_daytime_reference PRIVATE p6e_solar)
if(MSVC)
 target_compile_options(p6e_elustr_daytime_tests PRIVATE /W4 /WX)
 target_compile_options(p6e_elustr_daytime_reference PRIVATE /W4 /WX)
else()
 target_compile_options(p6e_elustr_daytime_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
 target_compile_options(p6e_elustr_daytime_reference PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6e_elustr_daytime_software COMMAND p6e_elustr_daytime_tests)

add_executable(p6e_cloud3_tests tests/cloud3_tests.cpp)
add_executable(p6e_cloud3_reference src/cloud3_reference_main.cpp)
target_link_libraries(p6e_cloud3_tests PRIVATE p6e_solar)
target_link_libraries(p6e_cloud3_reference PRIVATE p6e_solar)
if(MSVC)
 target_compile_options(p6e_cloud3_tests PRIVATE /W4 /WX)
 target_compile_options(p6e_cloud3_reference PRIVATE /W4 /WX)
else()
 target_compile_options(p6e_cloud3_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
 target_compile_options(p6e_cloud3_reference PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6e_cloud3_software COMMAND p6e_cloud3_tests)

add_executable(p6e_surfvar_multistation_tests tests/surfvar_multistation_tests.cpp)
add_executable(p6e_surfvar_multistation_reference src/surfvar_multistation_reference_main.cpp)
target_link_libraries(p6e_surfvar_multistation_tests PRIVATE p6e_solar)
target_link_libraries(p6e_surfvar_multistation_reference PRIVATE p6e_solar)
if(MSVC)
 target_compile_options(p6e_surfvar_multistation_tests PRIVATE /W4 /WX)
 target_compile_options(p6e_surfvar_multistation_reference PRIVATE /W4 /WX)
else()
 target_compile_options(p6e_surfvar_multistation_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
 target_compile_options(p6e_surfvar_multistation_reference PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6e_surfvar_multistation_software COMMAND p6e_surfvar_multistation_tests)

add_executable(p6e_mixhmc_tests tests/mixhmc_tests.cpp)
add_executable(p6e_mixhmc_reference src/mixhmc_reference_main.cpp)
target_link_libraries(p6e_mixhmc_tests PRIVATE p6e_solar)
target_link_libraries(p6e_mixhmc_reference PRIVATE p6e_solar)
if(MSVC)
 target_compile_options(p6e_mixhmc_tests PRIVATE /W4 /WX)
 target_compile_options(p6e_mixhmc_reference PRIVATE /W4 /WX)
else()
 target_compile_options(p6e_mixhmc_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
 target_compile_options(p6e_mixhmc_reference PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6e_mixhmc_software COMMAND p6e_mixhmc_tests)

add_executable(p6e_mixdt_tests tests/mixdt_tests.cpp)
add_executable(p6e_mixdt_reference src/mixdt_reference_main.cpp)
target_link_libraries(p6e_mixdt_tests PRIVATE p6e_solar)
target_link_libraries(p6e_mixdt_reference PRIVATE p6e_solar)
if(MSVC)
 target_compile_options(p6e_mixdt_tests PRIVATE /W4 /WX)
 target_compile_options(p6e_mixdt_reference PRIVATE /W4 /WX)
else()
 target_compile_options(p6e_mixdt_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
 target_compile_options(p6e_mixdt_reference PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6e_mixdt_software COMMAND p6e_mixdt_tests)

add_executable(p6e_mixht_observed_mc_tests tests/mixht_observed_mc_tests.cpp)
add_executable(p6e_mixht_observed_mc_reference src/mixht_observed_mc_reference_main.cpp)
target_link_libraries(p6e_mixht_observed_mc_tests PRIVATE p6e_solar)
target_link_libraries(p6e_mixht_observed_mc_reference PRIVATE p6e_solar)
if(MSVC)
 target_compile_options(p6e_mixht_observed_mc_tests PRIVATE /W4 /WX)
 target_compile_options(p6e_mixht_observed_mc_reference PRIVATE /W4 /WX)
else()
 target_compile_options(p6e_mixht_observed_mc_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
 target_compile_options(p6e_mixht_observed_mc_reference PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6e_mixht_observed_mc_software COMMAND p6e_mixht_observed_mc_tests)

add_executable(p6e_temp3d_observed_land_tests tests/temp3d_observed_land_tests.cpp)
add_executable(p6e_temp3d_observed_land_reference src/temp3d_observed_land_reference_main.cpp)
target_link_libraries(p6e_temp3d_observed_land_tests PRIVATE p6e_solar)
target_link_libraries(p6e_temp3d_observed_land_reference PRIVATE p6e_solar)
if(MSVC)
 target_compile_options(p6e_temp3d_observed_land_tests PRIVATE /W4 /WX)
 target_compile_options(p6e_temp3d_observed_land_reference PRIVATE /W4 /WX)
else()
 target_compile_options(p6e_temp3d_observed_land_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
 target_compile_options(p6e_temp3d_observed_land_reference PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6e_temp3d_observed_land_software COMMAND p6e_temp3d_observed_land_tests)

# E15 only consumes frozen P6C header contracts; does not modify P6C/P6D.
add_executable(p6e_p6c_hourly_bridge_tests tests/p6c_hourly_bridge_tests.cpp)
target_link_libraries(p6e_p6c_hourly_bridge_tests PRIVATE p6e_solar)
target_include_directories(p6e_p6c_hourly_bridge_tests PRIVATE ../include)
if(MSVC)
 target_compile_options(p6e_p6c_hourly_bridge_tests PRIVATE /W4 /WX)
else()
 target_compile_options(p6e_p6c_hourly_bridge_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6e_p6c_143h_hourly_boundary_contract COMMAND p6e_p6c_hourly_bridge_tests)

# Read-only real SURF.DAT/UP.DAT 2022 observation boundary trace.
add_executable(p6e_p6c_hourly_bridge src/p6c_hourly_bridge_main.cpp)
target_link_libraries(p6e_p6c_hourly_bridge PRIVATE p6e_solar)
target_include_directories(p6e_p6c_hourly_bridge PRIVATE ../include)
if(MSVC)
 target_compile_options(p6e_p6c_hourly_bridge PRIVATE /W4 /WX)
else()
 target_compile_options(p6e_p6c_hourly_bridge PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()

# E16 temporal software integration: existing P6C state -> P6E physics.
add_executable(p6e_p6c_143h_physics_tests tests/p6c_143h_physics_tests.cpp)
target_link_libraries(p6e_p6c_143h_physics_tests PRIVATE p6e_solar)
target_include_directories(p6e_p6c_143h_physics_tests PRIVATE ../include)
if(MSVC)
 target_compile_options(p6e_p6c_143h_physics_tests PRIVATE /W4 /WX)
else()
 target_compile_options(p6e_p6c_143h_physics_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6e_p6c_143h_mixht_temp3d_sequential_invariants COMMAND p6e_p6c_143h_physics_tests)

# E17 synthetic formatted SURF.DAT/UP.DAT to full 143h CLI end-to-end.
find_package(Python3 COMPONENTS Interpreter REQUIRED)
add_test(NAME p6e_p6c_143h_formatted_input_cli
  COMMAND "${Python3_EXECUTABLE}"
    "${CMAKE_CURRENT_SOURCE_DIR}/tests/verify_p6c_cli_formatted_143h.py"
    --cpp "$<TARGET_FILE:p6e_p6c_hourly_bridge>")

# E18 actual 2022 P6C original COMP observation trace (NOT source P6E physics).
add_test(NAME p6e_e18_real_2022_p6c_observed_temp3d_smoke
  COMMAND "${Python3_EXECUTABLE}"
  "${CMAKE_CURRENT_SOURCE_DIR}/tests/verify_real_2022_p6c_temp3d_replay.py"
  --fixture "${CMAKE_CURRENT_SOURCE_DIR}/reference/data/hefei_2022_p6c_original_obs.zlib.b64"
  --cpp "$<TARGET_FILE:p6e_temp3d_observed_land_reference>"
  --out "${CMAKE_CURRENT_BINARY_DIR}/e18-real2022-observed-replay.json")

# E19 Batchvarova-Gryning convective mixing height (original IMIXH=2 MIXHBG).
add_executable(p6e_mixhbg_tests tests/mixhbg_tests.cpp)
add_executable(p6e_mixhbg_reference src/mixhbg_reference_main.cpp)
target_link_libraries(p6e_mixhbg_tests PRIVATE p6e_solar)
target_link_libraries(p6e_mixhbg_reference PRIVATE p6e_solar)
if(MSVC)
 target_compile_options(p6e_mixhbg_tests PRIVATE /W4 /WX)
 target_compile_options(p6e_mixhbg_reference PRIVATE /W4 /WX)
else()
 target_compile_options(p6e_mixhbg_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
 target_compile_options(p6e_mixhbg_reference PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6e_mixhbg_software COMMAND p6e_mixhbg_tests)

# E21 real-case CALMET option profile contract (MIXHT->TEMP3D composed chain).
add_executable(p6e_realcase_options_tests tests/realcase_options_tests.cpp)
target_link_libraries(p6e_realcase_options_tests PRIVATE p6e_solar)
if(MSVC)
 target_compile_options(p6e_realcase_options_tests PRIVATE /W4 /WX)
else()
 target_compile_options(p6e_realcase_options_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6e_realcase_option_profile_contract COMMAND p6e_realcase_options_tests)

# E22 CALMET.DAT 2.1 output contract and truth-comparison harness.
add_executable(p6e_calmet_dat21 src/calmet_dat21_tool_main.cpp)
target_link_libraries(p6e_calmet_dat21 PRIVATE p6e_solar)
target_include_directories(p6e_calmet_dat21 PRIVATE ../include) # native P6D station MIXHTST physical contract
if(MSVC)
 target_compile_options(p6e_calmet_dat21 PRIVATE /W4 /WX)
else()
 target_compile_options(p6e_calmet_dat21 PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6e_calmet_dat21_output_contract
  COMMAND "${Python3_EXECUTABLE}"
    "${CMAKE_CURRENT_SOURCE_DIR}/tests/verify_calmet_dat21_contract.py"
    --tool "$<TARGET_FILE:p6e_calmet_dat21>"
    --harness "${CMAKE_CURRENT_SOURCE_DIR}/reference/compare_calmet_dat21.py")

# The frozen real CALMET.DAT 2.1 reference case is only present once
# project/cases/hefei5km_2022_reference_case_20261011 is in the checkout.
# When it is present the byte-exact round trip and the frozen SHA-256 become
# part of the CTest run; when it is absent the synthetic contract still runs.
set(P6E_REAL_MET_DAT
  "${CMAKE_CURRENT_SOURCE_DIR}/../../../../project/cases/hefei5km_2022_reference_case_20261011/run/met/met.dat")
set(P6E_REAL_MET_SHA256
  "b1823cda92280888d70b00961ab39486036a3086e18637fff21efb4f4b237d30")
if(EXISTS "${P6E_REAL_MET_DAT}")
  add_test(NAME p6e_calmet_dat21_real_reference_round_trip
    COMMAND "${Python3_EXECUTABLE}"
      "${CMAKE_CURRENT_SOURCE_DIR}/tests/verify_calmet_dat21_contract.py"
      --tool "$<TARGET_FILE:p6e_calmet_dat21>"
      --harness "${CMAKE_CURRENT_SOURCE_DIR}/reference/compare_calmet_dat21.py"
      --real-reference "${P6E_REAL_MET_DAT}"
      --real-reference-sha256 "${P6E_REAL_MET_SHA256}")
  message(STATUS "P6E real CALMET.DAT 2.1 reference test: REGISTERED (frozen SHA-256 pinned)")
else()
  message(STATUS "P6E real CALMET.DAT 2.1 reference test: not registered (reference case not in this checkout)")
endif()

# E42 acceptance, gate-visible: the frozen 143 h real case driven by the
# original CALMET.DAT wind (regime B) must give `dQSW == 0` for every hour and
# a `compare_calmet_dat21.py` PASS with 0 total exceedances over the 18
# P6E-owned fields.  The test locates the frozen case itself (checkout first,
# then the shared local-gate driver checkout) and reports BLOCKED - never a
# silent skip - when it is absent.
add_test(NAME p6e_calmet_dat21_real_full_field_reference
  COMMAND "${Python3_EXECUTABLE}"
    "${CMAKE_CURRENT_SOURCE_DIR}/tests/verify_real_2022_full_field_reference.py"
    --repo-root "${CMAKE_CURRENT_SOURCE_DIR}/../../../.."
    --bridge "$<TARGET_FILE:p6e_p6c_hourly_bridge>"
    --tool "$<TARGET_FILE:p6e_calmet_dat21>"
    --work "${CMAKE_CURRENT_BINARY_DIR}/e42-real-full-field")
set_tests_properties(p6e_calmet_dat21_real_full_field_reference
  PROPERTIES TIMEOUT 900)
message(STATUS "P6E real full-field reference test: REGISTERED (dQSW==0 + 0 exceedances)")

# E25 AVETMP upwind spatial averaging (IAVET=1) and airden surface density.
add_executable(p6e_avetmp_tests tests/avetmp_tests.cpp)
add_executable(p6e_avetmp_reference src/avetmp_reference_main.cpp)
target_link_libraries(p6e_avetmp_tests PRIVATE p6e_solar)
target_link_libraries(p6e_avetmp_reference PRIVATE p6e_solar)
if(MSVC)
 target_compile_options(p6e_avetmp_tests PRIVATE /W4 /WX)
 target_compile_options(p6e_avetmp_reference PRIVATE /W4 /WX)
else()
 target_compile_options(p6e_avetmp_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
 target_compile_options(p6e_avetmp_reference PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6e_avetmp_software COMMAND p6e_avetmp_tests)

# Original-source AVETMP parity runs whenever a Fortran compiler is present.
find_program(P6E_GFORTRAN NAMES gfortran-13 gfortran-12 gfortran-11 gfortran)
if(P6E_GFORTRAN)
  add_test(NAME p6e_avetmp_original_source_parity
    COMMAND "${Python3_EXECUTABLE}"
      "${CMAKE_CURRENT_SOURCE_DIR}/reference/compare_original_avetmp.py"
      --vendor "${CMAKE_CURRENT_SOURCE_DIR}/../../../../engine/vendor/src/CALMET_v6.5.0_L150223/calmet.for"
      --cpp "$<TARGET_FILE:p6e_avetmp_reference>"
      --gfortran "${P6E_GFORTRAN}"
      --out "${CMAKE_CURRENT_BINARY_DIR}/avetmp-original-parity.json")
  message(STATUS "P6E AVETMP original-source parity test: REGISTERED (${P6E_GFORTRAN})")
else()
  message(STATUS "P6E AVETMP original-source parity test: not registered (no Fortran compiler)")
endif()