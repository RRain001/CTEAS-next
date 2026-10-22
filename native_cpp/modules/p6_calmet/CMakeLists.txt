cmake_minimum_required(VERSION 3.20)
project(CTEAS_P6A_CALMET_CONTRACTS LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
add_library(cteas_p6a_contracts INTERFACE)
target_include_directories(cteas_p6a_contracts INTERFACE
                           ${CMAKE_CURRENT_SOURCE_DIR}/include
                           ${CMAKE_CURRENT_SOURCE_DIR}/p6e/include)
# G6 independent arbitrary-NX/NY GEO reader; frozen p6_read_geo/50 is unchanged.
add_executable(cteas_p6g_dynamic_geo_tests tests/p6g_dynamic_geo_tests.cpp)
target_link_libraries(cteas_p6g_dynamic_geo_tests PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6g_dynamic_geo_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_dynamic_geo_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6g_dynamic_geo_utm_and_frozen_field_parity COMMAND cteas_p6g_dynamic_geo_tests)

# Source-compatible dynamic station deck, segregated from frozen SS1/US1.
add_executable(cteas_p6g_station_set_tests tests/p6g_station_set_tests.cpp)
target_link_libraries(cteas_p6g_station_set_tests PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6g_station_set_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_station_set_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6g_multistation_readcf_real4_parity COMMAND cteas_p6g_station_set_tests)

# G7: native SURF.DAT v2.1 formatted multi-station and cross-year input.
# Frozen read_surface_2022 stays separate for independent 143h comparison.
add_executable(cteas_p6g_surface_dynamic_tests tests/p6g_surface_dynamic_tests.cpp)
target_link_libraries(cteas_p6g_surface_dynamic_tests PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6g_surface_dynamic_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_surface_dynamic_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6g_surface_multi_site_multiyear_frozen_143h_parity COMMAND cteas_p6g_surface_dynamic_tests)

# G7b: native READ62/RDUPN upper-air file-per-station, multiple soundings.
add_executable(cteas_p6g_upper_dynamic_tests tests/p6g_upper_dynamic_tests.cpp)
target_link_libraries(cteas_p6g_upper_dynamic_tests PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6g_upper_dynamic_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_upper_dynamic_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6g_upper_multi_site_multiyear_frozen_rdupn_parity COMMAND cteas_p6g_upper_dynamic_tests)

# G7c: SOURCE INPUT CONTRACT ONLY. No WIND1/COMP production physics.
add_executable(cteas_p6g_observation_input_tests tests/p6g_observation_input_tests.cpp)
target_link_libraries(cteas_p6g_observation_input_tests PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6g_observation_input_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_observation_input_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6g_multistation_surface_upper_hourly_input_contract COMMAND cteas_p6g_observation_input_tests)

# G8: 10 km multi-SURF/multi-UP cross-year and full 8784h leap-year
# source-selected INTER2/SIMILT/VERTAV/PREPDI computational integration only.
# This is NOT full CALMET WIND1/DIAGNO physical equivalence.
add_executable(cteas_p6g_g8_10km_year_tests tests/p6g_g8_10km_year_stress_tests.cpp)
target_link_libraries(cteas_p6g_g8_10km_year_tests PRIVATE cteas_p6a_contracts)
target_include_directories(cteas_p6g_g8_10km_year_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/p6e/include)
if(MSVC)
  target_compile_options(cteas_p6g_g8_10km_year_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_g8_10km_year_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6g_g8_multisite_10km_8784h_selected_source_bridge COMMAND cteas_p6g_g8_10km_year_tests)

# G9 independent multi-station WIND1 source-selected regression.
add_executable(cteas_p6g_g9_multi_wind1_tests tests/p6g_g9_multi_wind1_tests.cpp)
target_link_libraries(cteas_p6g_g9_multi_wind1_tests PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6g_g9_multi_wind1_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_g9_multi_wind1_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6g_g9_expanded_10km_multi_wind1_frozen_pair_parity COMMAND cteas_p6g_g9_multi_wind1_tests)

# G11 source-selected genuine TERSET→FRADJ→SLOPE, dynamic 10km grid.
# All thermodynamics are test-synthetic, NOT independently verified P6E.
add_executable(cteas_p6g_g11_terrain_tests tests/p6g_g11_source_terrain_tests.cpp)
target_link_libraries(cteas_p6g_g11_terrain_tests PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6g_g11_terrain_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_g11_terrain_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6g_g11_original_terrain_dynamic_10km_source_contract COMMAND cteas_p6g_g11_terrain_tests)

# G12 native source P6E selected SURFVAR+HEATFX 2-SS thermal bridge
# with hourly station identity, solar and gamma fail-closed contracts.
add_executable(cteas_p6g_g12_thermal_tests tests/p6g_g12_observed_p6e_thermal_tests.cpp)
target_link_libraries(cteas_p6g_g12_thermal_tests PRIVATE cteas_p6a_contracts)
target_include_directories(cteas_p6g_g12_thermal_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/p6e/include)
if(MSVC)
  target_compile_options(cteas_p6g_g12_thermal_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_g12_thermal_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6g_g12_10km_2surface_observed_temp_selected_heatfx_contract COMMAND cteas_p6g_g12_thermal_tests)



# G13 separate 10km original-source SURFVAR reference: do not reuse the old
# P6E 100m reference driver which silently defaults its DGRID to 100m.
add_executable(cteas_p6g_g13_surfvar_10km_reference src/p6g_g13_surfvar_10km_reference_main.cpp)
target_link_libraries(cteas_p6g_g13_surfvar_10km_reference PRIVATE cteas_p6a_contracts)
target_include_directories(cteas_p6g_g13_surfvar_10km_reference PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/p6e/include)
if(MSVC)
  target_compile_options(cteas_p6g_g13_surfvar_10km_reference PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_g13_surfvar_10km_reference PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()

# G10 original-Fortran 10km selected DIAGNO tail source-lift reference.
# Distinct from frozen 100m DIAGNO and from any real terrain/heat acceptance.
add_executable(cteas_p6g_g10_diagno_reference src/p6g_g10_10km_diagno_reference_main.cpp)
target_link_libraries(cteas_p6g_g10_diagno_reference PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6g_g10_diagno_reference PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_g10_diagno_reference PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()


set_tests_properties(p6g_g8_multisite_10km_8784h_selected_source_bridge PROPERTIES TIMEOUT 900)




# P6G G14: new dynamic 2SS/2US hourly state authority REUSES accepted
# P6SinglePass stage enums/order, but does NOT replace frozen P6D/P6E physics.
add_executable(cteas_p6g_g14_unified_hourly_tests tests/p6g_g14_unified_hourly_tests.cpp)
target_link_libraries(cteas_p6g_g14_unified_hourly_tests PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6g_g14_unified_hourly_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_g14_unified_hourly_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6g_g14_unified_2ss_2us_hourly_clock_state_1h_6h_143h_8784h
         COMMAND cteas_p6g_g14_unified_hourly_tests)

# G34B: selectable scientific experiment only, isolated from the accepted
# single-station physics and from all GUI/production G26 run() paths.
# The candidate must complete six real G14 state transactions, then the
# independent original 270-field numerical gate decides scientific parity.
add_executable(cteas_p6g_g34b_six_hour_selected_gate
               src/p6g_g34b_six_hour_selected_gate_main.cpp)
target_link_libraries(cteas_p6g_g34b_six_hour_selected_gate PRIVATE cteas_p6a_contracts)
# Link the EXACT frozen P6F serializer translation unit and include root,
# identically to the already verified G30 first-hour candidate.
target_sources(cteas_p6g_g34b_six_hour_selected_gate PRIVATE
               p6f/src/calmet_dat21_writer.cpp)
target_include_directories(cteas_p6g_g34b_six_hour_selected_gate PRIVATE
                           ${CMAKE_CURRENT_SOURCE_DIR}/p6f/include)
if(MSVC)
  target_compile_options(cteas_p6g_g34b_six_hour_selected_gate PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_g34b_six_hour_selected_gate PRIVATE
                         -Wall -Wextra -Wpedantic -Werror)
endif()

# G19: original file-backed 2SS/2US input provenance and G14 authority.
# This is NOT a successful 17-stage physical model or Fortran 45-field gate.
add_executable(cteas_p6g_g19_file_backed_case_tests
               tests/p6g_g19_file_backed_case_tests.cpp)
target_link_libraries(cteas_p6g_g19_file_backed_case_tests PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6g_g19_file_backed_case_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_g19_file_backed_case_tests PRIVATE
                         -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6g_g19_source_file_backed_2ss_2us_g14_input_contract
         COMMAND cteas_p6g_g19_file_backed_case_tests
           "${CMAKE_CURRENT_SOURCE_DIR}/../../../project/cases/hefei5km_2022_reference_case_20261011/run/met/met.inp")

# G19: native CLI to preflight ACTUAL 2SS/2US+ source files.
# Explicitly not a multistation CALMET physical solver.
add_executable(cteas_p6g_g19_source_case_preflight
               src/p6g_g19_source_case_preflight_main.cpp)
target_link_libraries(cteas_p6g_g19_source_case_preflight PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6g_g19_source_case_preflight PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_g19_source_case_preflight PRIVATE
                         -Wall -Wextra -Wpedantic -Werror)
endif()

# G20: independent source-file native first-hour WIND1 U/V diagnostic only.
# Generates an original-grid REAL4 text trace for future original-vendor
# comparisons. DOES NOT publish a G14 hour or claim full CALMET parity.
add_executable(cteas_p6g_g20_source_wind1_probe
               src/p6g_g20_source_wind1_probe_main.cpp)
target_link_libraries(cteas_p6g_g20_source_wind1_probe PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6g_g20_source_wind1_probe PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_g20_source_wind1_probe PRIVATE
                         -Wall -Wextra -Wpedantic -Werror)
endif()

# S4 P6-B2C: genuine 1US original upper VERTAV/PREPDI independent Fortran
# forensic input only. No resulting G23/INTER2 model hour is authorized.
add_executable(cteas_p6g_g20_real_1us_prepdi_export
               src/p6g_g20_real_1us_prepdi_export_main.cpp)
target_link_libraries(cteas_p6g_g20_real_1us_prepdi_export PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6g_g20_real_1us_prepdi_export PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_g20_real_1us_prepdi_export PRIVATE
                         -Wall -Wextra -Wpedantic -Werror)
endif()

# G21: compile source-file-driven native FRADJ/CGAMMA/SURFVAR first-hour
# audit. This is NOT an accepted production multi-station CALMET solver.
add_executable(cteas_p6g_g21_source_fradj_probe
               src/p6g_g21_source_fradj_probe_main.cpp)
target_link_libraries(cteas_p6g_g21_source_fradj_probe PRIVATE cteas_p6a_contracts)
# G30A: bind existing frozen P6F writer as a translation unit ONLY for
# selected first-hour 45-field candidate bytes. No new serializer,
# no replacement of accepted single-site physics.
target_sources(cteas_p6g_g21_source_fradj_probe PRIVATE
               p6f/src/calmet_dat21_writer.cpp)
target_include_directories(cteas_p6g_g21_source_fradj_probe PRIVATE
                           ${CMAKE_CURRENT_SOURCE_DIR}/p6f/include)
if(MSVC)
  target_compile_options(cteas_p6g_g21_source_fradj_probe PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_g21_source_fradj_probe PRIVATE
                         -Wall -Wextra -Wpedantic -Werror)
endif()

# G15A: no independently hardcoded G8 wind radii or BIAS; verify against
# the actual pinned 2022 met.inp with original READCF effective BIAS(1).
add_executable(cteas_p6g_g15_original_controls_tests
               tests/p6g_g15_original_wind_controls_tests.cpp)
target_link_libraries(cteas_p6g_g15_original_controls_tests PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6g_g15_original_controls_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_g15_original_controls_tests PRIVATE
                         -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6g_g15_original_metinp_wind_radii_bias_readcf_source
         COMMAND cteas_p6g_g15_original_controls_tests
           "${CMAKE_CURRENT_SOURCE_DIR}/../../../project/cases/hefei5km_2022_reference_case_20261011/run/met/met.inp")

# G16A: stage-correct WIND1/INTER2 adapter with mandatory post-SLOPE handoff.
# Does NOT claim fully coupled original CALMET hourly source parity.
add_executable(cteas_p6g_g16_staged_wind_tests
               tests/p6g_g16_staged_wind_tests.cpp)
target_link_libraries(cteas_p6g_g16_staged_wind_tests PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6g_g16_staged_wind_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_g16_staged_wind_tests PRIVATE
                         -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6g_g16_source_wind1_then_explicit_post_slope_inter2_no_comp
         COMMAND cteas_p6g_g16_staged_wind_tests
           "${CMAKE_CURRENT_SOURCE_DIR}/../../../project/cases/hefei5km_2022_reference_case_20261011/run/met/met.inp")

# G17A: selected source-ordered native FRADJ and SLOPE between G16 WIND1
# and INTER2, with first WINDBC snapshot and explicit fixture provenance.
add_executable(cteas_p6g_g17_staged_terrain_tests
               tests/p6g_g17_staged_terrain_tests.cpp)
target_link_libraries(cteas_p6g_g17_staged_terrain_tests PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6g_g17_staged_terrain_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_g17_staged_terrain_tests PRIVATE
                         -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6g_g17_fradj_slope_first_windbc_native_stage_source_parity
         COMMAND cteas_p6g_g17_staged_terrain_tests
           "${CMAKE_CURRENT_SOURCE_DIR}/../../../project/cases/hefei5km_2022_reference_case_20261011/run/met/met.inp")

# G17B1: original observed SURFVAR + computed UTC SOLAR + HEATFX,
# with explicit external ancillary fixture provenance, not full P6E.
add_executable(cteas_p6g_g17b_observed_solar_heat_tests
               tests/p6g_g17b_observed_solar_heat_tests.cpp)
target_link_libraries(cteas_p6g_g17b_observed_solar_heat_tests PRIVATE cteas_p6a_contracts)
target_include_directories(cteas_p6g_g17b_observed_solar_heat_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/p6e/include)
if(MSVC)
  target_compile_options(cteas_p6g_g17b_observed_solar_heat_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_g17b_observed_solar_heat_tests PRIVATE
                         -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6g_g17b_source_computed_utm_solar_multisite_surfvar_heatfx
         COMMAND cteas_p6g_g17b_observed_solar_heat_tests
           "${CMAKE_CURRENT_SOURCE_DIR}/../../../project/cases/hefei5km_2022_reference_case_20261011/run/met/met.inp")

# G17B3: CALMET source SETCOM initialises 1-based station NEARS, and
# AIRDEN uses nearest RDSN pressure plus SURFVAR TEMP2D. Compile literal
# Fortran source loop oracle, not hand-authored physical approximation.
add_executable(cteas_p6g_g17b_setcom_airden_reference
               src/p6g_g17b_setcom_airden_reference_main.cpp)
target_link_libraries(cteas_p6g_g17b_setcom_airden_reference PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6g_g17b_setcom_airden_reference PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_g17b_setcom_airden_reference PRIVATE
                         -Wall -Wextra -Wpedantic -Werror)
endif()
find_program(P6G_G17B_GFORTRAN NAMES gfortran-11 gfortran-12 gfortran)
find_package(Python3 QUIET COMPONENTS Interpreter)
if(P6G_G17B_GFORTRAN AND Python3_Interpreter_FOUND)
  add_test(NAME p6g_g17b_literal_vendor_setcom_nears_airden_real4_parity
    COMMAND "${Python3_EXECUTABLE}"
      "${CMAKE_CURRENT_SOURCE_DIR}/reference/compare_original_g17b_setcom_airden.py"
      --vendor "${CMAKE_CURRENT_SOURCE_DIR}/../../../engine/vendor/src/CALMET_v6.5.0_L150223/calmet.for"
      --cpp "$<TARGET_FILE:cteas_p6g_g17b_setcom_airden_reference>"
      --gfortran "${P6G_G17B_GFORTRAN}"
      --out "${CMAKE_CURRENT_BINARY_DIR}/g17b_setcom_airden_source_parity.json")
endif()

# G18B6: literal CALMET 6.5.0 SETCOM source NEARU (upper stations).
# Not an inferred analog from G17B surface NEARS; compare independent
# gfortran compiled original Fortran against production G18B3 at zero tolerance.
add_executable(cteas_p6g_g18b6_setcom_nearu_reference
               src/p6g_g18b6_setcom_nearu_reference_main.cpp)
target_link_libraries(cteas_p6g_g18b6_setcom_nearu_reference PRIVATE cteas_p6a_contracts)
target_include_directories(cteas_p6g_g18b6_setcom_nearu_reference PRIVATE
                           ${CMAKE_CURRENT_SOURCE_DIR}/p6e/include)
if(MSVC)
  target_compile_options(cteas_p6g_g18b6_setcom_nearu_reference PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_g18b6_setcom_nearu_reference PRIVATE
                         -Wall -Wextra -Wpedantic -Werror)
endif()
if(P6G_G17B_GFORTRAN AND Python3_Interpreter_FOUND)
  add_test(NAME p6g_g18b6_literal_vendor_setcom_nearu_multiup_real4_parity
    COMMAND "${Python3_EXECUTABLE}"
      "${CMAKE_CURRENT_SOURCE_DIR}/reference/compare_original_g18b6_setcom_nearu.py"
      --vendor "${CMAKE_CURRENT_SOURCE_DIR}/../../../engine/vendor/src/CALMET_v6.5.0_L150223/calmet.for"
      --cpp "$<TARGET_FILE:cteas_p6g_g18b6_setcom_nearu_reference>"
      --gfortran "${P6G_G17B_GFORTRAN}"
      --out "${CMAKE_CURRENT_BINARY_DIR}/g18b6_setcom_nearu_source_parity.json")
endif()

# G18B8: literal CALMET v6.5.0 IUPT GAMMA 1/R^2 and CMPD2 source
# fragments compiled with gfortran, REAL*4 bit-for-bit against production
# multi-site G18B8 C++ in both selected IUPT source branches.
add_executable(cteas_p6g_g18b8_gamma_grid_reference
               src/p6g_g18b8_gamma_grid_reference_main.cpp)
target_link_libraries(cteas_p6g_g18b8_gamma_grid_reference PRIVATE cteas_p6a_contracts)
target_include_directories(cteas_p6g_g18b8_gamma_grid_reference PRIVATE
                           ${CMAKE_CURRENT_SOURCE_DIR}/p6e/include)
if(MSVC)
  target_compile_options(cteas_p6g_g18b8_gamma_grid_reference PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_g18b8_gamma_grid_reference PRIVATE
                         -Wall -Wextra -Wpedantic -Werror)
endif()
if(P6G_G17B_GFORTRAN AND Python3_Interpreter_FOUND)
  add_test(NAME p6g_g18b8_literal_vendor_diagno_gamma_cmpd2_real4_parity
    COMMAND "${Python3_EXECUTABLE}"
      "${CMAKE_CURRENT_SOURCE_DIR}/reference/compare_original_g18b8_gamma_grid.py"
      --vendor "${CMAKE_CURRENT_SOURCE_DIR}/../../../engine/vendor/src/CALMET_v6.5.0_L150223/calmet.for"
      --cpp "$<TARGET_FILE:cteas_p6g_g18b8_gamma_grid_reference>"
      --gfortran "${P6G_G17B_GFORTRAN}"
      --out "${CMAKE_CURRENT_BINARY_DIR}/g18b8_gamma_source_parity.json")
endif()

# G18C1: source AVEMIX spatial averaging for IAVEZI=1, prior to WSTARR/TEMP3D.
# Unmodified literal vendor AVEMIX with a params.met dimension-only stub
# provides independent REAL*4 per-cell ZI/ZICONV numerical acceptance.
add_executable(cteas_p6g_g18c1_avemix_reference
               src/p6g_g18c1_avemix_reference_main.cpp)
target_link_libraries(cteas_p6g_g18c1_avemix_reference PRIVATE cteas_p6a_contracts)
target_include_directories(cteas_p6g_g18c1_avemix_reference PRIVATE
                           ${CMAKE_CURRENT_SOURCE_DIR}/p6e/include)
if(MSVC)
  target_compile_options(cteas_p6g_g18c1_avemix_reference PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_g18c1_avemix_reference PRIVATE
                         -Wall -Wextra -Wpedantic -Werror)
endif()
if(P6G_G17B_GFORTRAN AND Python3_Interpreter_FOUND)
  add_test(NAME p6g_g18c1_literal_vendor_avemix_zi_ziconv_real4_parity
    COMMAND "${Python3_EXECUTABLE}"
      "${CMAKE_CURRENT_SOURCE_DIR}/reference/compare_original_g18c1_avemix.py"
      --vendor "${CMAKE_CURRENT_SOURCE_DIR}/../../../engine/vendor/src/CALMET_v6.5.0_L150223/calmet.for"
      --cpp "$<TARGET_FILE:cteas_p6g_g18c1_avemix_reference>"
      --gfortran "${P6G_G17B_GFORTRAN}"
      --out "${CMAKE_CURRENT_BINARY_DIR}/g18c1_avemix_source_parity.json")
endif()

# G18D3: original CALMET BLOCK DATA HFLUX source defaults are NOT
# the old G17C HC1=HC2=0, HC3P1=1 synthetic coefficients.
add_executable(cteas_p6g_g18d3_hflux_defaults_reference
               src/p6g_g18d3_heat_source_defaults_reference_main.cpp)
target_link_libraries(cteas_p6g_g18d3_hflux_defaults_reference PRIVATE cteas_p6a_contracts)
target_include_directories(cteas_p6g_g18d3_hflux_defaults_reference PRIVATE
                           ${CMAKE_CURRENT_SOURCE_DIR}/p6e/include)
if(MSVC)
  target_compile_options(cteas_p6g_g18d3_hflux_defaults_reference PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_g18d3_hflux_defaults_reference PRIVATE
                         -Wall -Wextra -Wpedantic -Werror)
endif()
if(P6G_G17B_GFORTRAN AND Python3_Interpreter_FOUND)
  add_test(NAME p6g_g18d3_literal_vendor_hflux_block_data_real4_parity
    COMMAND "${Python3_EXECUTABLE}"
      "${CMAKE_CURRENT_SOURCE_DIR}/reference/compare_original_g18d3_hflux_defaults.py"
      --vendor "${CMAKE_CURRENT_SOURCE_DIR}/../../../engine/vendor/src/CALMET_v6.5.0_L150223/calmet.for"
      --cpp "$<TARGET_FILE:cteas_p6g_g18d3_hflux_defaults_reference>"
      --gfortran "${P6G_G17B_GFORTRAN}"
      --out "${CMAKE_CURRENT_BINARY_DIR}/g18d3_hflux_source_defaults_parity.json")
endif()

# G18D6: literal CALMET SETCOM NEARU closest-upper station grid mapping.
# Compiles actual G18B3 C++ module, independently extracts vendor Fortran
# READCF/SETCOM's REAL4 index loops, and compares every 1-based ordinal.
add_executable(cteas_p6g_g18d6_nearu_reference
               src/p6g_g18d6_nearu_reference_main.cpp)
target_link_libraries(cteas_p6g_g18d6_nearu_reference PRIVATE cteas_p6a_contracts)
target_include_directories(cteas_p6g_g18d6_nearu_reference PRIVATE
                           ${CMAKE_CURRENT_SOURCE_DIR}/p6e/include)
if(MSVC)
  target_compile_options(cteas_p6g_g18d6_nearu_reference PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_g18d6_nearu_reference PRIVATE
                         -Wall -Wextra -Wpedantic -Werror)
endif()
if(P6G_G17B_GFORTRAN AND Python3_Interpreter_FOUND)
  add_test(NAME p6g_g18d6_literal_vendor_setcom_nearu_real4_parity
    COMMAND "${Python3_EXECUTABLE}"
      "${CMAKE_CURRENT_SOURCE_DIR}/reference/compare_original_g18d6_nearu.py"
      --vendor "${CMAKE_CURRENT_SOURCE_DIR}/../../../engine/vendor/src/CALMET_v6.5.0_L150223/calmet.for"
      --cpp "$<TARGET_FILE:cteas_p6g_g18d6_nearu_reference>"
      --gfortran "${P6G_G17B_GFORTRAN}"
      --out "${CMAKE_CURRENT_BINARY_DIR}/g18d6_setcom_nearu_source_parity.json")
endif()

# G18D7: preserve DIAGI XSSTA/DX+1 REAL*4 semantics before INTEGER
# assignment; independently compile the literal original DIAGI and
# DIAGNO/STHEOR bound clamps. Frozen #53 physics remains unchanged.
add_executable(cteas_p6g_g18d7_diagi_cell_reference
               src/p6g_g18d7_diagi_cell_reference_main.cpp)
target_link_libraries(cteas_p6g_g18d7_diagi_cell_reference PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6g_g18d7_diagi_cell_reference PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_g18d7_diagi_cell_reference PRIVATE
                         -Wall -Wextra -Wpedantic -Werror)
endif()
if(P6G_G17B_GFORTRAN AND Python3_Interpreter_FOUND)
  add_test(NAME p6g_g18d7_literal_vendor_diagi_stheor_real4_site_cell_parity
    COMMAND "${Python3_EXECUTABLE}"
      "${CMAKE_CURRENT_SOURCE_DIR}/reference/compare_original_g18d7_diagi_cell.py"
      --vendor "${CMAKE_CURRENT_SOURCE_DIR}/../../../engine/vendor/src/CALMET_v6.5.0_L150223/calmet.for"
      --cpp "$<TARGET_FILE:cteas_p6g_g18d7_diagi_cell_reference>"
      --gfortran "${P6G_G17B_GFORTRAN}"
      --out "${CMAKE_CURRENT_BINARY_DIR}/g18d7_diagi_cell_source_parity.json")
endif()

# G17B4: original Hefei IAVET=1 two SURFVAR/AVETMP calls bracket FRADJ;
# distinct source WIND1 and post-FRADJ winds must not be conflated.
add_executable(cteas_p6g_g17b4_iavet_two_pass_tests
               tests/p6g_g17b4_iavet_two_pass_tests.cpp)
target_link_libraries(cteas_p6g_g17b4_iavet_two_pass_tests PRIVATE cteas_p6a_contracts)
# Compile the accepted original P6F writer as a separate translation unit:
# no reimplementation, no modifications to frozen #53 source files.
target_sources(cteas_p6g_g17b4_iavet_two_pass_tests PRIVATE
               p6f/src/calmet_dat21_writer.cpp)
target_include_directories(cteas_p6g_g17b4_iavet_two_pass_tests PRIVATE
                           ${CMAKE_CURRENT_SOURCE_DIR}/p6e/include
                           ${CMAKE_CURRENT_SOURCE_DIR}/p6f/include)
if(MSVC)
  target_compile_options(cteas_p6g_g17b4_iavet_two_pass_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_g17b4_iavet_two_pass_tests PRIVATE
                         -Wall -Wextra -Wpedantic -Werror)
endif()
set(P6G_G18C6_BINARY "${CMAKE_CURRENT_BINARY_DIR}/g18c6_selected_2ss_2us_1h_calmet.dat")
add_test(NAME p6g_g17b4_original_iavet1_pre_and_post_fradj_surfvar
         COMMAND cteas_p6g_g17b4_iavet_two_pass_tests
           "${CMAKE_CURRENT_SOURCE_DIR}/../../../project/cases/hefei5km_2022_reference_case_20261011/run/met/met.inp"
           "${P6G_G18C6_BINARY}")
add_test(NAME p6g_g18c6_independent_native_calmet_dat21_2ss_2us_byte_walk
  COMMAND "${Python3_EXECUTABLE}"
    "${CMAKE_CURRENT_SOURCE_DIR}/reference/verify_g18c6_independent_binary.py"
    --candidate "${P6G_G18C6_BINARY}"
    --out "${CMAKE_CURRENT_BINARY_DIR}/g18c6_binary_independent.json")
set_tests_properties(
  p6g_g18c6_independent_native_calmet_dat21_2ss_2us_byte_walk
  PROPERTIES DEPENDS p6g_g17b4_original_iavet1_pre_and_post_fradj_surfvar)

# Source-selected G17B4 must retain the independently audited original
# AVETMP Fortran parity (40 cases, source calmet.for unmodified).
add_executable(cteas_p6g_g17b4_avetmp_reference
               p6e/src/avetmp_reference_main.cpp)
target_link_libraries(cteas_p6g_g17b4_avetmp_reference PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6g_g17b4_avetmp_reference PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_g17b4_avetmp_reference PRIVATE
                         -Wall -Wextra -Wpedantic -Werror)
endif()
if(P6G_G17B_GFORTRAN AND Python3_Interpreter_FOUND)
  add_test(NAME p6g_g17b4_original_vendor_avetmp_40_case_source_parity
    COMMAND "${Python3_EXECUTABLE}"
      "${CMAKE_CURRENT_SOURCE_DIR}/p6e/reference/compare_original_avetmp.py"
      --vendor "${CMAKE_CURRENT_SOURCE_DIR}/../../../engine/vendor/src/CALMET_v6.5.0_L150223/calmet.for"
      --cpp "$<TARGET_FILE:cteas_p6g_g17b4_avetmp_reference>"
      --gfortran "${P6G_G17B_GFORTRAN}"
      --out "${CMAKE_CURRENT_BINARY_DIR}/g17b4_avetmp_original_source_parity.json")
endif()

add_executable(cteas_p6a_contract_tests tests/p6_contract_tests.cpp)
target_link_libraries(cteas_p6a_contract_tests PRIVATE cteas_p6a_contracts)
add_executable(cteas_p6_terset src/terrain_envelope_main.cpp)
target_link_libraries(cteas_p6_terset PRIVATE cteas_p6a_contracts)
add_executable(cteas_p6_terrain_envelope_tests tests/p6_terrain_envelope_tests.cpp)
target_link_libraries(cteas_p6_terrain_envelope_tests PRIVATE cteas_p6a_contracts)
add_executable(cteas_p6_fradj src/froude_adjust_main.cpp)
target_link_libraries(cteas_p6_fradj PRIVATE cteas_p6a_contracts)
add_executable(cteas_p6_fradj_tests tests/p6_froude_adjust_tests.cpp)
target_link_libraries(cteas_p6_fradj_tests PRIVATE cteas_p6a_contracts)
add_executable(cteas_p6_stations src/station_geometry_main.cpp)
target_link_libraries(cteas_p6_stations PRIVATE cteas_p6a_contracts)
add_executable(cteas_p6_station_tests tests/p6_station_geometry_tests.cpp)
target_link_libraries(cteas_p6_station_tests PRIVATE cteas_p6a_contracts)
add_executable(cteas_p6_read_geo src/read_geo_main.cpp)
target_link_libraries(cteas_p6_read_geo PRIVATE cteas_p6a_contracts)
add_executable(cteas_p6_geo_tests tests/p6_read_geo_tests.cpp)
target_link_libraries(cteas_p6_geo_tests PRIVATE cteas_p6a_contracts)
add_executable(cteas_p6_read_surface src/read_surface_main.cpp)
target_link_libraries(cteas_p6_read_surface PRIVATE cteas_p6a_contracts)
add_executable(cteas_p6_surface_tests tests/p6_read_surface_tests.cpp)
target_link_libraries(cteas_p6_surface_tests PRIVATE cteas_p6a_contracts)
add_executable(cteas_p6_read_upper src/read_upper_main.cpp)
target_link_libraries(cteas_p6_read_upper PRIVATE cteas_p6a_contracts)
add_executable(cteas_p6_upper_tests tests/p6_read_upper_tests.cpp)
target_link_libraries(cteas_p6_upper_tests PRIVATE cteas_p6a_contracts)
add_executable(cteas_p6_vertav src/vertical_wind_average_main.cpp)
target_link_libraries(cteas_p6_vertav PRIVATE cteas_p6a_contracts)
add_executable(cteas_p6_vertav_tests tests/p6_vertical_wind_average_tests.cpp)
target_link_libraries(cteas_p6_vertav_tests PRIVATE cteas_p6a_contracts)
add_executable(cteas_p6_upper_hourly src/upper_hourly_wind_main.cpp)
target_link_libraries(cteas_p6_upper_hourly PRIVATE cteas_p6a_contracts)
add_executable(cteas_p6_hourly_tests tests/p6_upper_hourly_wind_tests.cpp)
target_link_libraries(cteas_p6_hourly_tests PRIVATE cteas_p6a_contracts)
add_executable(cteas_p6_facet src/temperature_faces_main.cpp)
target_link_libraries(cteas_p6_facet PRIVATE cteas_p6a_contracts)
add_executable(cteas_p6_facet_tests tests/p6_temperature_faces_tests.cpp)
target_link_libraries(cteas_p6_facet_tests PRIVATE cteas_p6a_contracts)
add_executable(cteas_p6_comp_joint src/comp_joint_main.cpp)
target_link_libraries(cteas_p6_comp_joint PRIVATE cteas_p6a_contracts)
add_executable(cteas_p6_comp_buffered_tests tests/p6_comp_buffered_tests.cpp)
target_link_libraries(cteas_p6_comp_buffered_tests PRIVATE cteas_p6a_contracts)
add_executable(cteas_p6_rdsn_buffered_tests tests/p6_rdsn_buffered_tests.cpp)
target_link_libraries(cteas_p6_rdsn_buffered_tests PRIVATE cteas_p6a_contracts)
add_executable(cteas_p6_cgamma src/cgamma_main.cpp)
target_link_libraries(cteas_p6_cgamma PRIVATE cteas_p6a_contracts)
# Native CGAMMA integration: consume the previous-hour P6E MIXHT/AVEMIX
# convective state and export self-computed FRADJ lapse grids (NO Fortran
# GAMMA injection). This is explicitly one-station / fixed 143h only.
add_executable(cteas_p6_native_cgamma_grid_143h src/cgamma_from_p6e_143h_main.cpp)
target_link_libraries(cteas_p6_native_cgamma_grid_143h PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6_native_cgamma_grid_143h PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6_native_cgamma_grid_143h PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6_native_cgamma_grid_rejects_missing_state
  COMMAND cteas_p6_native_cgamma_grid_143h
    --up does-not-exist-up.dat
    --p6e-state-prefix does-not-exist-p6e-state
    --out ${CMAKE_CURRENT_BINARY_DIR}/missing-native-cgamma
    --zupt 200 --upper-i 25 --upper-j 26)
set_tests_properties(p6_native_cgamma_grid_rejects_missing_state
  PROPERTIES WILL_FAIL TRUE)
add_executable(cteas_p6_cgamma_tests tests/p6_cgamma_tests.cpp)
target_link_libraries(cteas_p6_cgamma_tests PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6_cgamma PRIVATE /W4 /WX)
  target_compile_options(cteas_p6_cgamma_tests PRIVATE /W4 /WX)
  target_compile_options(cteas_p6_rdsn_buffered_tests PRIVATE /W4 /WX)
  target_compile_options(cteas_p6_comp_joint PRIVATE /W4 /WX)
  target_compile_options(cteas_p6_comp_buffered_tests PRIVATE /W4 /WX)
  target_compile_options(cteas_p6_facet PRIVATE /W4 /WX)
  target_compile_options(cteas_p6_facet_tests PRIVATE /W4 /WX)
  target_compile_options(cteas_p6_upper_hourly PRIVATE /W4 /WX)
  target_compile_options(cteas_p6_hourly_tests PRIVATE /W4 /WX)
  target_compile_options(cteas_p6_vertav PRIVATE /W4 /WX)
  target_compile_options(cteas_p6_vertav_tests PRIVATE /W4 /WX)
  target_compile_options(cteas_p6_read_upper PRIVATE /W4 /WX)
  target_compile_options(cteas_p6_upper_tests PRIVATE /W4 /WX)
  target_compile_options(cteas_p6_read_surface PRIVATE /W4 /WX)
  target_compile_options(cteas_p6_surface_tests PRIVATE /W4 /WX)
  target_compile_options(cteas_p6_read_geo PRIVATE /W4 /WX)
  target_compile_options(cteas_p6_geo_tests PRIVATE /W4 /WX)
  target_compile_options(cteas_p6_stations PRIVATE /W4 /WX)
  target_compile_options(cteas_p6_station_tests PRIVATE /W4 /WX)
  target_compile_options(cteas_p6_fradj PRIVATE /W4 /WX)
  target_compile_options(cteas_p6_fradj_tests PRIVATE /W4 /WX)
  target_compile_options(cteas_p6_terset PRIVATE /W4 /WX)
  target_compile_options(cteas_p6_terrain_envelope_tests PRIVATE /W4 /WX)
  target_compile_options(cteas_p6a_contract_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6_cgamma PRIVATE -Wall -Wextra -Wpedantic -Werror)
  target_compile_options(cteas_p6_cgamma_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
  target_compile_options(cteas_p6_rdsn_buffered_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
  target_compile_options(cteas_p6_comp_joint PRIVATE -Wall -Wextra -Wpedantic -Werror)
  target_compile_options(cteas_p6_comp_buffered_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
  target_compile_options(cteas_p6a_contract_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
  target_compile_options(cteas_p6_terset PRIVATE -Wall -Wextra -Wpedantic -Werror)
  target_compile_options(cteas_p6_terrain_envelope_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
  target_compile_options(cteas_p6_fradj PRIVATE -Wall -Wextra -Wpedantic -Werror)
  target_compile_options(cteas_p6_fradj_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
  target_compile_options(cteas_p6_stations PRIVATE -Wall -Wextra -Wpedantic -Werror)
  target_compile_options(cteas_p6_station_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
  target_compile_options(cteas_p6_read_geo PRIVATE -Wall -Wextra -Wpedantic -Werror)
  target_compile_options(cteas_p6_geo_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
  target_compile_options(cteas_p6_read_surface PRIVATE -Wall -Wextra -Wpedantic -Werror)
  target_compile_options(cteas_p6_surface_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
  target_compile_options(cteas_p6_read_upper PRIVATE -Wall -Wextra -Wpedantic -Werror)
  target_compile_options(cteas_p6_upper_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
  target_compile_options(cteas_p6_vertav PRIVATE -Wall -Wextra -Wpedantic -Werror)
  target_compile_options(cteas_p6_vertav_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
  target_compile_options(cteas_p6_upper_hourly PRIVATE -Wall -Wextra -Wpedantic -Werror)
  target_compile_options(cteas_p6_hourly_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
  target_compile_options(cteas_p6_facet PRIVATE -Wall -Wextra -Wpedantic -Werror)
  target_compile_options(cteas_p6_facet_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
enable_testing()
add_test(NAME p6a_calmet_scoped_contracts COMMAND cteas_p6a_contract_tests)
add_test(NAME p6c_terrain_envelope_software COMMAND cteas_p6_terrain_envelope_tests)
add_test(NAME p6d_froude_adjust_software COMMAND cteas_p6_fradj_tests)
add_test(NAME p6c_station_geometry_software COMMAND cteas_p6_station_tests)
add_test(NAME p6c_geo_selected_scoped_software COMMAND cteas_p6_geo_tests)
add_test(NAME p6c_surface_selected_scoped_software COMMAND cteas_p6_surface_tests)
add_test(NAME p6c_upper_rdupn_selected_scoped_software COMMAND cteas_p6_upper_tests)
add_test(NAME p6c_original_vertav_software COMMAND cteas_p6_vertav_tests)
add_test(NAME p6c_hourly_prepdi_software COMMAND cteas_p6_hourly_tests)
add_test(NAME p6c_original_facet_intp_software COMMAND cteas_p6_facet_tests)
add_test(NAME p6c_comp_buffered_candidate_software COMMAND cteas_p6_comp_buffered_tests)
add_test(NAME p6c_rdsn_buffered_state_candidate COMMAND cteas_p6_rdsn_buffered_tests)
add_test(NAME p6c_original_cgamma_state_candidate COMMAND cteas_p6_cgamma_tests)

# P6D independent SLOPE kernel -- not a diagnostic-wind integration claim.
add_executable(cteas_p6_slope src/slope_flow_main.cpp)
target_link_libraries(cteas_p6_slope PRIVATE cteas_p6a_contracts)
add_executable(cteas_p6_slope_tests tests/p6_slope_flow_tests.cpp)
target_link_libraries(cteas_p6_slope_tests PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6_slope PRIVATE /W4 /WX)
  target_compile_options(cteas_p6_slope_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6_slope PRIVATE -Wall -Wextra -Wpedantic -Werror)
  target_compile_options(cteas_p6_slope_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6d_original_slope_software COMMAND cteas_p6_slope_tests)

# P6D DIVCEL source-scoped divergence kernel. MINIM not yet integrated.
add_executable(cteas_p6_divcel src/divcel_main.cpp)
target_link_libraries(cteas_p6_divcel PRIVATE cteas_p6a_contracts)
add_executable(cteas_p6_divcel_tests tests/p6_divcel_tests.cpp)
target_link_libraries(cteas_p6_divcel_tests PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6_divcel PRIVATE /W4 /WX)
  target_compile_options(cteas_p6_divcel_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6_divcel PRIVATE -Wall -Wextra -Wpedantic -Werror)
  target_compile_options(cteas_p6_divcel_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6d_original_divcel_software COMMAND cteas_p6_divcel_tests)

# P6D source-scoped MINIM + WINDBC, using independently verified DIVCEL.
add_executable(cteas_p6_minim src/minim_main.cpp)
target_link_libraries(cteas_p6_minim PRIVATE cteas_p6a_contracts)
add_executable(cteas_p6_minim_tests tests/p6_minim_tests.cpp)
target_link_libraries(cteas_p6_minim_tests PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6_minim PRIVATE /W4 /WX)
  target_compile_options(cteas_p6_minim_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6_minim PRIVATE -Wall -Wextra -Wpedantic -Werror)
  target_compile_options(cteas_p6_minim_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6d_original_minim_software COMMAND cteas_p6_minim_tests)

# P6D selected non-lake-breeze SMOOTH, original Fortran parity gate.
add_executable(cteas_p6_smooth src/smooth_main.cpp)
target_link_libraries(cteas_p6_smooth PRIVATE cteas_p6a_contracts)
add_executable(cteas_p6_smooth_tests tests/p6_smooth_tests.cpp)
target_link_libraries(cteas_p6_smooth_tests PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6_smooth PRIVATE /W4 /WX)
  target_compile_options(cteas_p6_smooth_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6_smooth PRIVATE -Wall -Wextra -Wpedantic -Werror)
  target_compile_options(cteas_p6_smooth_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6d_original_smooth_software COMMAND cteas_p6_smooth_tests)

# P6D selected DIAGNO L6119-L6148 SMOOTH+DIVCEL+W+WINDBC segment.
add_executable(cteas_p6_final_segment src/diagno_segment_main.cpp)
target_link_libraries(cteas_p6_final_segment PRIVATE cteas_p6a_contracts)
add_executable(cteas_p6_final_segment_tests tests/p6_diagno_segment_tests.cpp)
target_link_libraries(cteas_p6_final_segment_tests PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6_final_segment PRIVATE /W4 /WX)
  target_compile_options(cteas_p6_final_segment_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6_final_segment PRIVATE -Wall -Wextra -Wpedantic -Werror)
  target_compile_options(cteas_p6_final_segment_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6d_original_diagno_final_segment_software COMMAND cteas_p6_final_segment_tests)

# P6D selected DIAGNO INTER2, real observation/first-guess route, not full WIND1.
add_executable(cteas_p6_inter2 src/inter2_selected_main.cpp)
target_link_libraries(cteas_p6_inter2 PRIVATE cteas_p6a_contracts)
add_executable(cteas_p6_inter2_tests tests/p6_inter2_selected_tests.cpp)
target_link_libraries(cteas_p6_inter2_tests PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6_inter2 PRIVATE /W4 /WX)
  target_compile_options(cteas_p6_inter2_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6_inter2 PRIVATE -Wall -Wextra -Wpedantic -Werror)
  target_compile_options(cteas_p6_inter2_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6d_original_inter2_selected_software COMMAND cteas_p6_inter2_tests)

# P6D selected WIND1 IEXTRP=-4 calls neutral SIMILT (not full WIND1).
add_executable(cteas_p6_similt_profile src/similt_profile_main.cpp)
target_link_libraries(cteas_p6_similt_profile PRIVATE cteas_p6a_contracts)
add_executable(cteas_p6_similt_profile_tests tests/p6_similt_profile_tests.cpp)
target_link_libraries(cteas_p6_similt_profile_tests PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6_similt_profile PRIVATE /W4 /WX)
  target_compile_options(cteas_p6_similt_profile_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6_similt_profile PRIVATE -Wall -Wextra -Wpedantic -Werror)
  target_compile_options(cteas_p6_similt_profile_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6d_original_similt_profile_software COMMAND cteas_p6_similt_profile_tests)

# P6D8A scoped WIND1 surface/upper observation wiring; not full WIND1 parity.
add_executable(cteas_p6_wind1_hour_tests tests/p6_wind1_selected_station_hour_tests.cpp)
target_link_libraries(cteas_p6_wind1_hour_tests PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6_wind1_hour_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6_wind1_hour_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6d8_wind1_selected_hour_observation_contract COMMAND cteas_p6_wind1_hour_tests)

# P6D8B selected original WIND1 first-guess grid (not full DIAGNO).
add_executable(cteas_p6_wind1_firstguess src/wind1_firstguess_main.cpp)
target_link_libraries(cteas_p6_wind1_firstguess PRIVATE cteas_p6a_contracts)
add_executable(cteas_p6_wind1_firstguess_tests tests/p6_wind1_selected_firstguess_tests.cpp)
target_link_libraries(cteas_p6_wind1_firstguess_tests PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6_wind1_firstguess PRIVATE /W4 /WX)
  target_compile_options(cteas_p6_wind1_firstguess_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6_wind1_firstguess PRIVATE -Wall -Wextra -Wpedantic -Werror)
  target_compile_options(cteas_p6_wind1_firstguess_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6d8b_original_wind1_firstguess_selected_software COMMAND cteas_p6_wind1_firstguess_tests)

# P6D9A source-scoped WIND1 -> INTER2 -> SMOOTH/DIVCEL/W bridge.
# Heat/terrain/slope effects MUST be supplied externally or explicitly bypassed
# in synthetic source-only audit mode; this does not qualify full DIAGNO.
add_executable(cteas_p6_d9a_bridge_tests tests/p6_diagno_d9a_bridge_tests.cpp)
target_link_libraries(cteas_p6_d9a_bridge_tests PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6_d9a_bridge_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6_d9a_bridge_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6d9a_wind1_inter2_diagno_selected_bridge_contract COMMAND cteas_p6_d9a_bridge_tests)

# P6D9A selected DIAGNO IOBR=1 tail: original L6153-L6159 O'Brien W
# adjustment plus L6180 MINIM. Upstream terrain/heat/slope still excluded.
add_executable(cteas_p6_obrien_minim_tests tests/p6_diagno_obrien_minim_tests.cpp)
target_link_libraries(cteas_p6_obrien_minim_tests PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6_obrien_minim_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6_obrien_minim_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6d9a_obrien_minim_iobr1_tail_contract COMMAND cteas_p6_obrien_minim_tests)

# P6D9A selected origin IFRADJ=1 upstream route: original FRADJ L5643-L5644
# on the step-one winds, before the L5748 boundary snapshot and INTER2.
add_executable(cteas_p6_fradj_route_tests tests/p6_diagno_fradj_route_tests.cpp)
target_link_libraries(cteas_p6_fradj_route_tests PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6_fradj_route_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6_fradj_route_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6d9a_fradj_upstream_route_contract COMMAND cteas_p6_fradj_route_tests)

# P6D9A selected original ISLOPE=1 upstream route: SLOPE L5722-L5723 plus the
# L5727-L5732 additive loop after FRADJ, before L5748/L6055/L6059.
add_executable(cteas_p6_slope_route_tests tests/p6_diagno_slope_route_tests.cpp)
target_link_libraries(cteas_p6_slope_route_tests PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6_slope_route_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6_slope_route_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6d9a_slope_upstream_route_contract COMMAND cteas_p6_slope_route_tests)

# P6D9A selected original IKINE=1 pre-blend kinematic route: W zeroing
# L5615-L5616, TOPOF2 L5621-L5622 and MINIM L5628-L5629.
add_executable(cteas_p6_topof2_route_tests tests/p6_diagno_topof2_route_tests.cpp)
target_link_libraries(cteas_p6_topof2_route_tests PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6_topof2_route_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6_topof2_route_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6d9a_topof2_preblend_route_contract COMMAND cteas_p6_topof2_route_tests)

# P6D9A in-chain original TERSET envelope (DIAGI L5228, I3DCTW=IWFCOD=1 in the
# real deck) replacing the caller-supplied HMAX/HMIN/DISTH* planes.
add_executable(cteas_p6_terset_envelope_tests tests/p6_diagno_terset_envelope_tests.cpp)
target_link_libraries(cteas_p6_terset_envelope_tests PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6_terset_envelope_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6_terset_envelope_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6d9a_inchain_terset_envelope_contract COMMAND cteas_p6_terset_envelope_tests)

# Original CALMET met.inp station positions: UTM kilometres -> REAL*4
# relative metres (not the auxiliary CSV geographic projection).
add_executable(cteas_p6_station_deck_tests tests/p6_station_deck_input_tests.cpp)
target_link_libraries(cteas_p6_station_deck_tests PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6_station_deck_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6_station_deck_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
# Isolated P6 kernel workflows sometimes fetch just C++ sources, not the
# multi-gigabyte frozen Hefei case. They must still test the source in isolation
# and must NOT claim real-case verification. The dedicated Mode A job requires
# full case inputs and fails configuration when any required artifact is absent.
option(CTEAS_P6_MODE_A_REQUIRE_CASE
       "Require complete frozen Hefei input tree for P6 Mode A numerical gates" OFF)
set(P6_MODEA_CASE
    "${CMAKE_CURRENT_SOURCE_DIR}/../../../project/cases/hefei5km_2022_reference_case_20261011")
set(P6_MODEA_REQUIRED_FILES
    "case.yaml"
    "grid/grid.cmn"
    "grid/center_location"
    "geo/terrel/terrel.inp"
    "geo/ctgproc/ctgproc.inp"
    "geo/makegeo/makegeo.inp"
    "geo/makegeo/geo.dat"
    "run/met/met.inp"
    "met/surface/final/stations.csv"
    "met/surface/final/surf.dat"
    "met/upperair/final/stations.csv"
    "met/upperair/final/up_58424.dat")
set(P6_MODEA_CASE_READY TRUE)
foreach(item IN LISTS P6_MODEA_REQUIRED_FILES)
  if(NOT EXISTS "${P6_MODEA_CASE}/${item}")
    set(P6_MODEA_CASE_READY FALSE)
    if(CTEAS_P6_MODE_A_REQUIRE_CASE)
      message(FATAL_ERROR "P6 Mode A required frozen-case input missing: ${P6_MODEA_CASE}/${item}")
    endif()
  endif()
endforeach()
add_test(NAME p6d_original_station_deck_synthetic_source_contract
         COMMAND cteas_p6_station_deck_tests)
if(P6_MODEA_CASE_READY)
  find_package(Python3 REQUIRED COMPONENTS Interpreter)
  add_test(NAME p6d_original_metinp_station_deck_input
           COMMAND cteas_p6_station_deck_tests "${P6_MODEA_CASE}/run/met/met.inp")
  add_test(NAME p6d_p3_p4_p5_metinp_station_contract
           COMMAND ${Python3_EXECUTABLE}
             "${CMAKE_CURRENT_SOURCE_DIR}/tests/check_case_station_contract.py"
             "${P6_MODEA_CASE}")
  add_test(NAME p6_modea_original_grid_generator_to_metinp
           COMMAND ${Python3_EXECUTABLE}
             "${CMAKE_CURRENT_SOURCE_DIR}/tests/check_case_grid_source_contract.py"
             "${P6_MODEA_CASE}")
  find_program(P6_STATION_GFORTRAN NAMES gfortran-11 gfortran-12 gfortran)
  if(P6_STATION_GFORTRAN)
    add_test(NAME p6d_original_readcf_real4_fortran_source
             COMMAND ${Python3_EXECUTABLE}
               "${CMAKE_CURRENT_SOURCE_DIR}/reference/compare_original_deck_station.py"
               --vendor "${CMAKE_CURRENT_SOURCE_DIR}/../../../engine/vendor/src/CALMET_v6.5.0_L150223/calmet.for"
               --deck "${P6_MODEA_CASE}/run/met/met.inp"
               --compiler ${P6_STATION_GFORTRAN}
               --out "${CMAKE_CURRENT_BINARY_DIR}/original_readcf_station")
  elseif(CTEAS_P6_MODE_A_REQUIRE_CASE)
    message(FATAL_ERROR "P6 Mode A original Fortran source oracle requires gfortran")
  else()
    message(STATUS "P6 original Fortran source oracle unavailable; not certified")
  endif()
else()
  message(STATUS "P6 Mode A full-case tests NOT REGISTERED; source-only CTests are still valid")
endif()

# P6D station-only original MIXHTST source-state transition probe.
# The prior COMP state is supplied as a forensic fixture, never as a native
# end-to-end wind acceptance input. The production recurrence remains pending.
add_executable(cteas_p6_station_mixhtst_probe src/station_mixhtst_probe_main.cpp)
target_link_libraries(cteas_p6_station_mixhtst_probe PRIVATE cteas_p6a_contracts)
target_include_directories(cteas_p6_station_mixhtst_probe PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/p6e/include)
if(MSVC)
  target_compile_options(cteas_p6_station_mixhtst_probe PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6_station_mixhtst_probe PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()

# P6D real-case wind-field producer (partial product: WIND1 step-one UG/VG
# plus the in-chain TERSET envelope, with explicit provenance metadata).
add_executable(cteas_p6_realcase_wind_field src/realcase_wind_field_main.cpp)
target_link_libraries(cteas_p6_realcase_wind_field PRIVATE cteas_p6a_contracts)
# Read-only reuse of the P6E submodule headers (SURFVAR/SOLAR/HEATFX); no P6E
# source is modified and the P6E module keeps its own build.
if(EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/p6e/include)
  target_include_directories(cteas_p6_realcase_wind_field PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/p6e/include)
else()
  message(FATAL_ERROR "P6E submodule headers required by the real-case producer are missing")
endif()
if(MSVC)
  target_compile_options(cteas_p6_realcase_wind_field PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6_realcase_wind_field PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()

# Native C++ single-clock, fail-closed P6D->P6E hourly *process adapter*.
# This transitional executable uses existing verified physics programs,
# carries no new physical formulas, and is NOT the final in-process adapter.
# Reuse P6F's independently tested SHA256 implementation to pin the frozen
# Fortran case rather than weakening the existing Python coordinator checks.
if(UNIX)
  add_executable(cteas_p6_native_hourly_driver
    src/native_hourly_driver_main.cpp p6f/src/sha256.cpp)
  target_include_directories(cteas_p6_native_hourly_driver PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/p6f/include
    ${CMAKE_CURRENT_SOURCE_DIR}/include)
  target_compile_options(cteas_p6_native_hourly_driver PRIVATE
    -Wall -Wextra -Wpedantic -Werror)
  add_test(NAME p6_native_cpp_hourly_driver_fail_closed_missing_case
    COMMAND cteas_p6_native_hourly_driver
      --case does-not-exist-native-hourly-case
      --p6d $<TARGET_FILE:cteas_p6_realcase_wind_field>
      --p6e does-not-exist-p6e
      --bridge does-not-exist-bridge --cgamma does-not-exist-cgamma
      --work ${CMAKE_CURRENT_BINARY_DIR}/missing-hourly-case)
  set_tests_properties(p6_native_cpp_hourly_driver_fail_closed_missing_case
    PROPERTIES WILL_FAIL TRUE)
  add_executable(cteas_p6_native_comp_history_tests
    tests/p6_native_comp_history_tests.cpp)
  target_link_libraries(cteas_p6_native_comp_history_tests PRIVATE cteas_p6a_contracts)
  target_compile_options(cteas_p6_native_comp_history_tests PRIVATE
    -Wall -Wextra -Wpedantic -Werror)
  add_test(NAME p6_native_cpp_comp_history_state_and_rollback
    COMMAND cteas_p6_native_comp_history_tests
      ${CMAKE_CURRENT_BINARY_DIR}/native_comp_history_ctest)
endif()

# Fail-closed contract run of the real-case producer on the frozen 5 km case
# tree (read-only inputs; outputs go to the build tree). The producer throws on
# any missing or invalid case input, so exit status plus the emitted hour count
# is the whole assertion.
if(P6_MODEA_CASE_READY)
  add_test(NAME p6d_realcase_wind_producer_case_contract
           COMMAND cteas_p6_realcase_wind_field
                   --case "${P6_MODEA_CASE}"
                   --out ${CMAKE_CURRENT_BINARY_DIR}/realcase_wind_ctest)
  set_tests_properties(p6d_realcase_wind_producer_case_contract PROPERTIES
                       PASS_REGULAR_EXPRESSION "hours=143")
endif()

# P6D9A composed trace for chained unmodified original Fortran comparisons.
add_executable(cteas_p6_d9a_source_trace src/diagno_d9a_trace_main.cpp)
target_link_libraries(cteas_p6_d9a_source_trace PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6_d9a_source_trace PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6_d9a_source_trace PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
# S2-G1B-B1 standalone REAL IGRA -> native P4 READ62 -> UP.DAT source-only
# preflight: validates genuine 6201 bytes and hourly AA/BB brackets only.
# This executable never runs numerical CALMET or CALPUFF physical kernels.
add_executable(cteas_p6g_up_source_preflight src/p6g_up_source_preflight_main.cpp)
target_link_libraries(cteas_p6g_up_source_preflight PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6g_up_source_preflight PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_up_source_preflight PRIVATE
    -Wall -Wextra -Wpedantic -Werror)
endif()

# S2-G1B-B2: real original NOAA-produced native P5 SURF independent input
# validation, not CALMET diagnostic winds or CALPUFF concentrations.
add_executable(cteas_p6g_surf_source_preflight src/p6g_surf_source_preflight_main.cpp)
target_link_libraries(cteas_p6g_surf_source_preflight PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6g_surf_source_preflight PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_surf_source_preflight PRIVATE
    -Wall -Wextra -Wpedantic -Werror)
endif()

# S4-B1: isolated genuine G19->G14 source admission for a future unified
# production actor. Not a WIND/COMP/P6F implementation or science result.
add_executable(cteas_p6g_s4b1_source_admission
               src/p6g_s4b1_source_admission_main.cpp)
target_link_libraries(cteas_p6g_s4b1_source_admission PRIVATE cteas_p6a_contracts)
add_executable(cteas_p6g_s4b1_admission_tests
               tests/p6g_s4b1_admission_tests.cpp)
target_link_libraries(cteas_p6g_s4b1_admission_tests PRIVATE cteas_p6a_contracts)
foreach(s4b1_target cteas_p6g_s4b1_source_admission cteas_p6g_s4b1_admission_tests)
  if(MSVC)
    target_compile_options(${s4b1_target} PRIVATE /W4 /WX)
  else()
    target_compile_options(${s4b1_target} PRIVATE -Wall -Wextra -Wpedantic -Werror)
  endif()
endforeach()
add_test(NAME p6g_s4b1_independent_station_cardinality_source_admission
         COMMAND cteas_p6g_s4b1_admission_tests)
add_test(NAME p6g_s4b1_refuses_unaccepted_production_execute
         COMMAND cteas_p6g_s4b1_source_admission --execute)
set_tests_properties(p6g_s4b1_refuses_unaccepted_production_execute
                     PROPERTIES WILL_FAIL TRUE)

# S4-B2: shared C2 accepted 17-stage G14 actor, with an independently
# configurable original-G19 source-only experimental entry point. It
# is NOT a production-supported P6 or a new-site CALMET science gate.
add_executable(cteas_p6g_s4b2_unified_selected
               src/p6g_s4b2_unified_selected_main.cpp
               p6f/src/calmet_dat21_writer.cpp)
target_link_libraries(cteas_p6g_s4b2_unified_selected PRIVATE cteas_p6a_contracts)
target_include_directories(cteas_p6g_s4b2_unified_selected PRIVATE
                           ${CMAKE_CURRENT_SOURCE_DIR}/p6f/include)
if(MSVC)
  target_compile_options(cteas_p6g_s4b2_unified_selected PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_s4b2_unified_selected PRIVATE
                         -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6g_s4b2_no_implicit_production
         COMMAND cteas_p6g_s4b2_unified_selected --met missing.met)
set_tests_properties(p6g_s4b2_no_implicit_production PROPERTIES WILL_FAIL TRUE)

# S4-B4: read the frozen original C1 MET (143h), produce a separate 1h
# original subset for independent P6E 45-field comparison. No native
# forecast values are injected into this reference-only utility.
add_executable(cteas_p6g_s4b4_extract_original_c1_first_hour
               src/p6g_s4b4_original_c1_first_hour_main.cpp)
target_link_libraries(cteas_p6g_s4b4_extract_original_c1_first_hour
                      PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6g_s4b4_extract_original_c1_first_hour
                         PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_s4b4_extract_original_c1_first_hour
                         PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()

# S4-O: ONLY a narrow original WATER/NOWSTA=0 reference-numeric slice
# on 63 observed water cells x six original hours. It does NOT compute ZI,
# admit native G14/G26, or weaken the old G18D3 all-land physics gate.
add_executable(cteas_p6g_g35_original_nowsta0_water_reference
               src/p6g_g35_original_noow_water_reference_main.cpp)
target_link_libraries(cteas_p6g_g35_original_nowsta0_water_reference
                      PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6g_g35_original_nowsta0_water_reference
                         PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_g35_original_nowsta0_water_reference
                         PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6g_g35_test_only_original_water_neutral_negative_guards
         COMMAND cteas_p6g_g35_original_nowsta0_water_reference --self-test)

# S4-P: source-restricted ZI/ZIMECH original WATER neutral mixing-height
# scalar NUMERICAL REFERENCE ONLY. G19/G14/G26 still do not call this.
add_executable(cteas_p6g_g36_original_nowsta0_water_zi
               src/p6g_g36_original_noow_water_zi_main.cpp)
target_link_libraries(cteas_p6g_g36_original_nowsta0_water_zi PRIVATE
                      cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6g_g36_original_nowsta0_water_zi PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_g36_original_nowsta0_water_zi PRIVATE
                         -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6g_g36_test_only_original_water_zi_negative_guards
         COMMAND cteas_p6g_g36_original_nowsta0_water_zi --self-test)

# S4-Q: original CALMET real WATER U10/V10 source alias and SETCOM FCORI.
# STRICT TEST ONLY; not a native wind solution or water G14/G26 admission.
add_executable(cteas_p6g_g37_original_water_fcori_ws10
               src/p6g_g37_original_water_fcori_ws10_main.cpp)
target_link_libraries(cteas_p6g_g37_original_water_fcori_ws10 PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6g_g37_original_water_fcori_ws10 PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_g37_original_water_fcori_ws10 PRIVATE
                         -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6g_g37_original_water_fcori_ws10_invalid_source_guards
         COMMAND cteas_p6g_g37_original_water_fcori_ws10 --self-test)

# S4-R0: selected original no-overwater-observations HEATFX source
# admission ONLY. Original G18D3 all-land G14/G26 remains fail-closed.
add_executable(cteas_p6g_g38_selected_water_hflux_source
               src/p6g_g38_selected_water_hflux_source_main.cpp)
target_link_libraries(cteas_p6g_g38_selected_water_hflux_source
                      PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6g_g38_selected_water_hflux_source
                         PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_g38_selected_water_hflux_source
                         PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6g_g38_selected_water_hflux_no_production_guards
         COMMAND cteas_p6g_g38_selected_water_hflux_source --self-test)

# S4-R1a: source-scoped no-OW water SURFVAR -> HEATFX -> ELUSTR only.
# Existing all-land G17B4/G17C1/G17C2 default water refusal unchanged.
# Original WATER USTAR/EL/ZI, G24 wind and G14/G26 remain NOT_ACCEPTED.
add_executable(cteas_p6g_g39_selected_water_thermal_reference
               src/p6g_g39_selected_water_thermal_reference_main.cpp)
target_link_libraries(cteas_p6g_g39_selected_water_thermal_reference
                      PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6g_g39_selected_water_thermal_reference
                         PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_g39_selected_water_thermal_reference
                         PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6g_g39_selected_water_thermal_source_and_production_denial
         COMMAND cteas_p6g_g39_selected_water_thermal_reference --self-test)

# S4-R1b authentic 82x85 NOAA no-OW WATER: native-only QSW input
# radiation and preserved water QH, independent original scratch comparison.
# Source-only CLI; no full G22/G24/G26 stage promotion.
add_executable(cteas_p6g_g40_real_water_shortwave_source
               src/p6g_g40_real_water_shortwave_source_main.cpp)
target_link_libraries(cteas_p6g_g40_real_water_shortwave_source
                      PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6g_g40_real_water_shortwave_source
                         PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_g40_real_water_shortwave_source
                         PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()

# S4-R1c1 authentic no-OW WATER source-only first-hour G20/G21/G39.
# It does not execute/produce native G24, COMP, P6F or a G14 commit.
add_executable(cteas_p6g_g41_real_water_first_hour
               src/p6g_g41_real_water_first_hour_main.cpp)
target_link_libraries(cteas_p6g_g41_real_water_first_hour
                      PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6g_g41_real_water_first_hour
                         PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_g41_real_water_first_hour
                         PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()

# S4-R1c2: original COMP MISSFC model-local nonwind replacement ONLY,
# source-owned raw P5 SURF remains byte-identical and never overwritten.
add_executable(cteas_p6g_g43_original_comp_missfc_source
               src/p6g_g43_original_comp_missfc_source_main.cpp)
target_link_libraries(cteas_p6g_g43_original_comp_missfc_source
                      PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6g_g43_original_comp_missfc_source
                         PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_g43_original_comp_missfc_source
                         PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()

# S4-R1c3 authentic 2SS/1US/63-WATER NOAA, G43 model-internal
# original MISSFC -> real G21 SURFVAR/FRADJ -> G39 HEATFX/AIRDEN/ELUSTR
# first-hour science ONLY, not original WATER USTAR/EL, G24/G26 or P7.
add_executable(cteas_p6g_g44_real_missfc_thermal_first_hour
               src/p6g_g44_real_missfc_thermal_first_hour_main.cpp)
target_link_libraries(cteas_p6g_g44_real_missfc_thermal_first_hour
                      PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6g_g44_real_missfc_thermal_first_hour
                         PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_g44_real_missfc_thermal_first_hour
                         PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()

# S4-R1c4a only: six actual consecutive source hours of 2SS+1US WIND1
# with P5 missing/calm masks. No prior-ZICONV model-state or G21/G39
# multi-hour physical admission, no G24, full 45-field G26 or P7.
add_executable(cteas_p6g_g45_six_hour_water_wind1
               src/p6g_g45_six_hour_water_wind1_main.cpp)
target_link_libraries(cteas_p6g_g45_six_hour_water_wind1
                      PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6g_g45_six_hour_water_wind1
                         PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_g45_six_hour_water_wind1
                         PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()

# S4-R1c4b: independent original/native 6970-cell first-hour WIND1,
# FRADJ + 2x SURFVAR fields; no G14 historical state/G24/G26/P7.
add_executable(cteas_p6g_g46_real_allgrid_g21_firsthour
               src/p6g_g46_real_allgrid_g21_firsthour_main.cpp)
target_link_libraries(cteas_p6g_g46_real_allgrid_g21_firsthour
                      PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6g_g46_real_allgrid_g21_firsthour
                         PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_g46_real_allgrid_g21_firsthour
                         PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()

# S4-R1c6 genuine NOAA first-hour post-ELUSTR original SLOPE, all grid
# nine levels. Source-only research gate, NOT G23/G24/G26/P7 admission.
add_executable(cteas_p6g_g47_real_water_post_slope
               src/p6g_g47_real_water_post_slope_main.cpp)
target_link_libraries(cteas_p6g_g47_real_water_post_slope
                      PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6g_g47_real_water_post_slope PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_g47_real_water_post_slope
                         PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()

# S4-R1c7b: real P5 sparse SS original STHEOR station kernel reuse after G47.
# Test-only: not full G23 INTER2, G24 final wind, COMP or P7.
add_executable(cteas_p6g_g48_real_sparse_stheor
               src/p6g_g48_real_sparse_stheor_main.cpp)
target_link_libraries(cteas_p6g_g48_real_sparse_stheor
                      PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6g_g48_real_sparse_stheor PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_g48_real_sparse_stheor
                         PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()

# S4-R1c7d: source-count-invariant G17C3 sparse SS ordinal merge contract.
# The test cannot be promoted into original/native INTER2 science.
add_executable(cteas_p6g_g17c3_sparse_ordinal_merge_tests
               tests/p6g_g17c3_sparse_ordinal_merge_tests.cpp)
target_link_libraries(cteas_p6g_g17c3_sparse_ordinal_merge_tests
                      PRIVATE cteas_p6a_contracts)
target_include_directories(cteas_p6g_g17c3_sparse_ordinal_merge_tests PRIVATE
                           ${CMAKE_CURRENT_SOURCE_DIR}/p6e/include)
if(MSVC)
  target_compile_options(cteas_p6g_g17c3_sparse_ordinal_merge_tests
                         PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_g17c3_sparse_ordinal_merge_tests
                         PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME p6g_g17c3_sparse_original_source_ordinals
         COMMAND cteas_p6g_g17c3_sparse_ordinal_merge_tests)

# S4-R1c7f: strict test-only real NOAA G16 INTER2 U/V science comparator
# Native executable never accepts any original CALMET U/V as runtime input.
add_executable(cteas_p6g_g49_real_sparse_inter2
               src/p6g_g49_real_sparse_inter2_main.cpp)
target_link_libraries(cteas_p6g_g49_real_sparse_inter2
                      PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6g_g49_real_sparse_inter2 PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_g49_real_sparse_inter2
                         PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()

# S4-R1c8a: true source-only G24 real NOAA first-hour final wind diagnostic.
add_executable(cteas_p6g_g50_real_noaa_g24_tail
               src/p6g_g50_real_noaa_g24_tail_main.cpp)
target_link_libraries(cteas_p6g_g50_real_noaa_g24_tail
                      PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6g_g50_real_noaa_g24_tail PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_g50_real_noaa_g24_tail
                         PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()

# S4-R1c8b real NOAA shared G17B4 third COMP SURFVAR candidate only.
add_executable(cteas_p6g_g51_real_noaa_comp_third
               src/p6g_g51_real_noaa_comp_third_main.cpp)
target_link_libraries(cteas_p6g_g51_real_noaa_comp_third
                      PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6g_g51_real_noaa_comp_third PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_g51_real_noaa_comp_third
                         PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()

# S4-R1c8c: only true G41 source partition for WATER COMP, no physical stages.
add_executable(cteas_p6g_g52_real_water_comp_partition
               src/p6g_g52_real_water_comp_partition_main.cpp)
target_link_libraries(cteas_p6g_g52_real_water_comp_partition
                      PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6g_g52_real_water_comp_partition
                         PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_g52_real_water_comp_partition
                         PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()

# S4-R1c8d: source-only final NOAA G24 -> original neutral WATER G37/G35/G36
add_executable(cteas_p6g_g53_real_g24_water_comp_neutral
               src/p6g_g53_real_water_comp_neutral_main.cpp)
target_link_libraries(cteas_p6g_g53_real_g24_water_comp_neutral
                      PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6g_g53_real_g24_water_comp_neutral
                         PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_g53_real_g24_water_comp_neutral
                         PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()

# S4-R1c8f: real NOAA source-only LAND MIXHT then whole-grid AVEMIX.
add_executable(cteas_p6g_g54_real_land_mixht
               src/p6g_g54_real_land_mixht_main.cpp)
target_link_libraries(cteas_p6g_g54_real_land_mixht
                      PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6g_g54_real_land_mixht PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_g54_real_land_mixht
                         PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()

# S4-R1c8g: native true COMP WSTARR after genuine firsthour AVEMIX.
add_executable(cteas_p6g_g55_real_comp_wstarr
               src/p6g_g55_real_comp_wstarr_main.cpp)
target_link_libraries(cteas_p6g_g55_real_comp_wstarr
                      PRIVATE cteas_p6a_contracts)
if(MSVC)
  target_compile_options(cteas_p6g_g55_real_comp_wstarr PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p6g_g55_real_comp_wstarr
                         PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
