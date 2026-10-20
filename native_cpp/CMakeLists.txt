cmake_minimum_required(VERSION 3.20)
project(CTEAS_Reconstruction LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
find_package(GDAL REQUIRED)
add_library(cteas_geo_inputs STATIC src/geo/terrain.cpp src/geo/landuse.cpp)
target_include_directories(cteas_geo_inputs PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(cteas_geo_inputs PUBLIC GDAL::GDAL)
if(MSVC)
  target_compile_options(cteas_geo_inputs PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_geo_inputs PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_executable(cteas_geo_inspect src/inspect_geo_inputs.cpp)
target_link_libraries(cteas_geo_inspect PRIVATE cteas_geo_inputs)
enable_testing()
add_executable(cteas_p1_input_tests tests/p1_input_tests.cpp)
target_link_libraries(cteas_p1_input_tests PRIVATE cteas_geo_inputs)
add_test(NAME cteas_p1_input_contracts COMMAND cteas_p1_input_tests)
add_executable(cteas_p2_input_tests tests/p2_input_tests.cpp)
target_link_libraries(cteas_p2_input_tests PRIVATE cteas_geo_inputs)
add_test(NAME cteas_p2_input_contracts COMMAND cteas_p2_input_tests)

# P2 GEN-only subset (no claim of full CTGPROC equivalence).
add_library(cteas_p2_gen STATIC src/geo/landuse_fraction.cpp)
target_include_directories(cteas_p2_gen PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(cteas_p2_gen PUBLIC cteas_geo_inputs)
add_executable(cteas_p2_gen_fraction src/p2_gen_fraction_cli.cpp)
target_link_libraries(cteas_p2_gen_fraction PRIVATE cteas_p2_gen)
add_executable(cteas_p2_gen_tests tests/p2_gen_fraction_tests.cpp)
target_link_libraries(cteas_p2_gen_tests PRIVATE cteas_p2_gen)
add_test(NAME cteas_p2_gen_fraction_contract COMMAND cteas_p2_gen_tests)

# Issue #123: isolate the original Fortran LUGRID / SVGRID point controls.
# Does NOT link or alter the frozen P2-B EXACT_AREA_V1 producer.
add_executable(cteas_p2_original_coast_policy_tests
               tests/p2_original_coast_policy_tests.cpp)
target_include_directories(cteas_p2_original_coast_policy_tests
                           PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)
if(MSVC)
  target_compile_options(cteas_p2_original_coast_policy_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p2_original_coast_policy_tests
                         PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME cteas_p2_original_coast_policy_synthetic
         COMMAND cteas_p2_original_coast_policy_tests)

# Issue #123 D2: isolated GSHHG Full L1-L4 IPTYPE software adapter.
# No production pipeline is linked to this non-Fortran-parity code.
add_library(cteas_p2_original_iptype STATIC src/geo/ctgproc_original_iptype.cpp)
target_include_directories(cteas_p2_original_iptype PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(cteas_p2_original_iptype PUBLIC GDAL::GDAL)
if(MSVC)
  target_compile_options(cteas_p2_original_iptype PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p2_original_iptype PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_executable(cteas_p2_original_iptype_tests tests/p2_original_iptype_tests.cpp)
target_link_libraries(cteas_p2_original_iptype_tests PRIVATE cteas_p2_original_iptype)
if(MSVC)
  target_compile_options(cteas_p2_original_iptype_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p2_original_iptype_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME cteas_p2_original_full_iptype_synthetic
         COMMAND cteas_p2_original_iptype_tests)

# Issue #123 D4: read original COASTRD-extracted BLN and emulate PNPOLY
# with REAL*4 intermediates (synthetic only, not an original Fortran PASS).
# Independent of the GEOS D2 adapter and of all production P2 code paths.
add_library(cteas_p2_original_bln_pnpoly STATIC
            src/geo/ctgproc_original_bln_pnpoly.cpp)
target_include_directories(cteas_p2_original_bln_pnpoly
                           PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
if(MSVC)
  target_compile_options(cteas_p2_original_bln_pnpoly PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p2_original_bln_pnpoly
                         PRIVATE -Wall -Wextra -Wpedantic -Werror -ffp-contract=off)
endif()
add_executable(cteas_p2_original_bln_pnpoly_tests
               tests/p2_original_bln_pnpoly_tests.cpp)
target_link_libraries(cteas_p2_original_bln_pnpoly_tests
                      PRIVATE cteas_p2_original_bln_pnpoly)
if(MSVC)
  target_compile_options(cteas_p2_original_bln_pnpoly_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p2_original_bln_pnpoly_tests
                         PRIVATE -Wall -Wextra -Wpedantic -Werror -ffp-contract=off)
endif()
add_test(NAME cteas_p2_original_bln_pnpoly_synthetic
         COMMAND cteas_p2_original_bln_pnpoly_tests)
# D4 manual same-input oracle driver, no production CLI integration.
# Issue #123 D8: isolated native classifier for SHA-gated authentic BLN
# and identical REAL*4 points compared against original Fortran IPTYPE.
# No production/original-mode integration or GLCC output parity is implied.
add_executable(cteas_p2_original_iptype_bln_batch
               src/p2_original_iptype_bln_batch_cli.cpp)
target_link_libraries(cteas_p2_original_iptype_bln_batch
                      PRIVATE cteas_p2_original_bln_pnpoly)
if(NOT MSVC)
  target_compile_options(cteas_p2_original_iptype_bln_batch PRIVATE
                         -Wall -Wextra -Wpedantic -Werror -ffp-contract=off)
endif()

add_executable(cteas_p2_original_pnpoly_batch
               src/p2_original_pnpoly_batch_cli.cpp)
target_link_libraries(cteas_p2_original_pnpoly_batch
                      PRIVATE cteas_p2_original_bln_pnpoly)
if(MSVC)
  target_compile_options(cteas_p2_original_pnpoly_batch PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p2_original_pnpoly_batch
                         PRIVATE -Wall -Wextra -Wpedantic -Werror -ffp-contract=off)
endif()

# Enforce case-grid precision independently from data availability.
add_executable(cteas_grid_origin_precision_tests tests/grid_origin_precision_tests.cpp)
target_include_directories(cteas_grid_origin_precision_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)
add_test(NAME cteas_grid_origin_three_decimal_km COMMAND cteas_grid_origin_precision_tests)

# Issue #53 D2: offline GLC_FCS30D raw-class area fractions (no crosswalk/P3).
add_library(cteas_p2_glc_area STATIC src/geo/glc_area_fractions.cpp)
target_include_directories(cteas_p2_glc_area PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(cteas_p2_glc_area PUBLIC cteas_p2_gen GDAL::GDAL)
if(MSVC)
  target_compile_options(cteas_p2_glc_area PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p2_glc_area PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_executable(cteas_p2_glc_area_tests tests/p2_glc_area_tests.cpp)
target_link_libraries(cteas_p2_glc_area_tests PRIVATE cteas_p2_glc_area)
add_test(NAME cteas_p2_glc_raw_area_contract COMMAND cteas_p2_glc_area_tests)
find_package(OpenSSL REQUIRED COMPONENTS Crypto)
add_executable(cteas_p2_glc_raw src/p2_glc_area_cli.cpp)
target_link_libraries(cteas_p2_glc_raw PRIVATE cteas_p2_glc_area OpenSSL::Crypto)
if(MSVC)
  target_compile_options(cteas_p2_glc_raw PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p2_glc_raw PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()

# Issue #53 D1: genuine raw GLCC binary reader and GEN replay comparator.
add_library(cteas_p2_glcc_source STATIC src/geo/glcc_raw_fractions.cpp)
target_include_directories(cteas_p2_glcc_source PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(cteas_p2_glcc_source PUBLIC cteas_p2_gen GDAL::GDAL)
if(MSVC)
  target_compile_options(cteas_p2_glcc_source PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p2_glcc_source PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_executable(cteas_p2_glcc_raw src/p2_glcc_raw_cli.cpp)
target_link_libraries(cteas_p2_glcc_raw PRIVATE cteas_p2_glcc_source OpenSSL::Crypto)
add_executable(cteas_p2_glcc_gen_test_driver tests/p2_glcc_gen_test_driver.cpp)
target_link_libraries(cteas_p2_glcc_gen_test_driver PRIVATE cteas_p2_glcc_source)

# Issue #123 D3: opt-in coastal RECOUNT from immutable P2-A source mesh trace.
# This deliberately links no production CLI; baseline GLCC and frozen
# Wolsong EXACT_AREA_V1 remain unchanged.
add_library(cteas_p2_original_sampling_recount STATIC
            src/geo/ctgproc_original_sampling_recount.cpp)
target_include_directories(cteas_p2_original_sampling_recount
                           PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
# The original Fortran-faithful Wolsong/Hefei numerical chain MUST NOT
# transitively link the synthetic GEOS D2 surrogate.
target_link_libraries(cteas_p2_original_sampling_recount PUBLIC
                      cteas_p2_original_bln_pnpoly cteas_p2_glcc_source)
if(MSVC)
  target_compile_options(cteas_p2_original_sampling_recount PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p2_original_sampling_recount
                         PRIVATE -Wall -Wextra -Wpedantic -Werror
                                 -ffp-contract=off)
endif()
# Issue #160 C2: D2 GEOS classifier remains test-only for public API
# regression, but is not linked by actual source-faithful C++ production.
# Both variants compile the SAME integer bookkeeping template. Exactly one
# overload/fraction implementation is emitted by the build definition.
add_library(cteas_p2_original_sampling_d2_surrogate STATIC
            src/geo/ctgproc_original_sampling_recount.cpp)
target_include_directories(cteas_p2_original_sampling_d2_surrogate
                           PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_compile_definitions(cteas_p2_original_sampling_d2_surrogate
                           PRIVATE CTEAS_P2_D2_GEOS_DIAGNOSTIC_ONLY=1)
target_link_libraries(cteas_p2_original_sampling_d2_surrogate PUBLIC
                      cteas_p2_original_sampling_recount
                      cteas_p2_original_iptype)
if(MSVC)
  target_compile_options(cteas_p2_original_sampling_d2_surrogate PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p2_original_sampling_d2_surrogate PRIVATE
                         -Wall -Wextra -Wpedantic -Werror -ffp-contract=off)
endif()

add_executable(cteas_p2_original_sampling_recount_tests
               tests/p2_original_sampling_recount_tests.cpp)
# Synthetic compatibility tests exercise BOTH D2 and BLN code paths.
target_link_libraries(cteas_p2_original_sampling_recount_tests
                      PRIVATE cteas_p2_original_sampling_d2_surrogate)
if(MSVC)
  target_compile_options(cteas_p2_original_sampling_recount_tests
                         PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p2_original_sampling_recount_tests
                         PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
add_test(NAME cteas_p2_original_sampling_recount_synthetic
         COMMAND cteas_p2_original_sampling_recount_tests)

# Issue #123 D9: isolated real-BLN original GLAZAS LFINAL=F integer HITS candidate.
# Scientific parity only through an independently SHA-audited real run.
add_executable(cteas_p2_original_coast_hits_wolsong
               src/p2_original_coast_hits_wolsong_cli.cpp)
target_link_libraries(cteas_p2_original_coast_hits_wolsong
                      PRIVATE cteas_p2_original_sampling_recount)
if(NOT MSVC)
  target_compile_options(cteas_p2_original_coast_hits_wolsong PRIVATE
                         -Wall -Wextra -Wpedantic -Werror -ffp-contract=off)
endif()

# Issue #123 D11: strictly opt-in, original-source scoped GLCC+real BLN
# LU.DAT v2.1 C++ production entrypoint. Not the frozen EXACT_AREA_V1 route.
add_executable(cteas_p2_original_sampling_wolsong
               src/p2_original_sampling_wolsong_cli.cpp)
target_link_libraries(cteas_p2_original_sampling_wolsong PRIVATE
                      cteas_p2_original_sampling_recount OpenSSL::Crypto)
if(MSVC)
  target_compile_options(cteas_p2_original_sampling_wolsong PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p2_original_sampling_wolsong PRIVATE
                         -Wall -Wextra -Wpedantic -Werror -ffp-contract=off)
endif()
add_executable(cteas_p2_original_sampling_lu_tests
               tests/p2_original_sampling_lu_writer_tests.cpp)
target_link_libraries(cteas_p2_original_sampling_lu_tests PRIVATE
                      cteas_p2_original_sampling_recount)
if(MSVC)
  target_compile_options(cteas_p2_original_sampling_lu_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p2_original_sampling_lu_tests PRIVATE
                         -Wall -Wextra -Wpedantic -Werror -ffp-contract=off)
endif()
add_test(NAME cteas_p2_original_sampling_lu_writer_synthetic
         COMMAND cteas_p2_original_sampling_lu_tests)

# Issue #160 C1: Hefei inland historical GLCC original-style sampling.
# Same canonical GLCC source, direct GLAZAS/LUGRID and original writer as
# Wolsong D11, but with LCOAST=F and EPSG:32650. No modern GLC area method.
add_executable(cteas_p2_original_sampling_hefei
               src/p2_original_sampling_hefei_cli.cpp)
target_link_libraries(cteas_p2_original_sampling_hefei PRIVATE
                      cteas_p2_original_sampling_recount GDAL::GDAL OpenSSL::Crypto)
if(MSVC)
  target_compile_options(cteas_p2_original_sampling_hefei PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p2_original_sampling_hefei PRIVATE
                         -Wall -Wextra -Wpedantic -Werror -ffp-contract=off)
endif()

# #160 C4: 30m modern source-pixel/GLAZAS integer HITS, separate from
# historical GLCC and P2-B EXACT_AREA_V1 and test-only GEOS surrogate.
add_library(cteas_p2c_glc30m_sampling STATIC
            src/geo/p2c_glc30m_sampling.cpp)
target_include_directories(cteas_p2c_glc30m_sampling
                           PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(cteas_p2c_glc30m_sampling PUBLIC
                      cteas_p2_original_sampling_recount GDAL::GDAL)
if(MSVC)
  target_compile_options(cteas_p2c_glc30m_sampling PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p2c_glc30m_sampling PRIVATE
                         -Wall -Wextra -Wpedantic -Werror -ffp-contract=off)
endif()
add_executable(cteas_p2c_glc30m_sampling_tests
               tests/p2c_glc30m_sampling_tests.cpp)
target_link_libraries(cteas_p2c_glc30m_sampling_tests PRIVATE
                      cteas_p2c_glc30m_sampling GDAL::GDAL)
if(MSVC)
  target_compile_options(cteas_p2c_glc30m_sampling_tests PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p2c_glc30m_sampling_tests PRIVATE
                         -Wall -Wextra -Wpedantic -Werror -ffp-contract=off)
endif()
add_test(NAME cteas_p2c_glc30m_synthetic_integer_conservation
         COMMAND cteas_p2c_glc30m_sampling_tests
         ${CMAKE_SOURCE_DIR}/../docs/plans/ISSUE53_GLC35_USGS38_USER_SELECTED_20261019.json)
add_executable(cteas_p2c_glc30m_sampling
               src/p2c_glc30m_sampling_cli.cpp)
target_link_libraries(cteas_p2c_glc30m_sampling PRIVATE
                      cteas_p2c_glc30m_sampling OpenSSL::Crypto)
if(MSVC)
  target_compile_options(cteas_p2c_glc30m_sampling PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p2c_glc30m_sampling PRIVATE
                         -Wall -Wextra -Wpedantic -Werror -ffp-contract=off)
endif()

# Issue #53 D3: SHA-bound historical GLCC 24->38 LU.DAT serializer only.
# The GLC_FCS30D 35->38 crosswalk remains scientifically unapproved.
add_executable(cteas_p2_glcc_lu_dat src/p2_glcc_lu_dat_cli.cpp)
target_link_libraries(cteas_p2_glcc_lu_dat PRIVATE cteas_p2_glcc_source GDAL::GDAL OpenSSL::Crypto)
if(MSVC)
  target_compile_options(cteas_p2_glcc_lu_dat PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p2_glcc_lu_dat PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()

# Issue #53 P2-B native source-gated GLC35 -> GSHHS Full land 52 / sea 55 -> USGS38 LU.DAT.
# Never reuse GLCC historical D3 source gate; original MAKEGEO/P6 science remains separate.
add_executable(cteas_p2_glc_lu_dat src/p2_glc_lu_dat_cli.cpp)
target_link_libraries(cteas_p2_glc_lu_dat PRIVATE cteas_p2_glc_area GDAL::GDAL OpenSSL::Crypto)
if(MSVC)
  target_compile_options(cteas_p2_glc_lu_dat PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p2_glc_lu_dat PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
