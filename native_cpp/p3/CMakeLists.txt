cmake_minimum_required(VERSION 3.20)
project(CTEAS_P3_MAKEGEO LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
add_executable(cteas_p3_makegeo ../src/p3_makegeo_cli.cpp)
if(MSVC)
  target_compile_options(cteas_p3_makegeo PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p3_makegeo PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()

# S2-2B: independent scoped ASCII writer, without changing P1/P2/P3 physics.
add_executable(cteas_p12_to_p3_dat p12_native_dat_adapter.cpp)
if(MSVC)
  target_compile_options(cteas_p12_to_p3_dat PRIVATE /W4 /WX)
else()
  target_compile_options(cteas_p12_to_p3_dat PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
find_package(Python3 COMPONENTS Interpreter REQUIRED)
enable_testing()
add_test(NAME cteas_p12_p3_scoped_file_contract
  COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_p12_p3_contract.py
    --adapter $<TARGET_FILE:cteas_p12_to_p3_dat>
    --p3 $<TARGET_FILE:cteas_p3_makegeo>
    --root ${CMAKE_CURRENT_SOURCE_DIR}/../..)
set_tests_properties(cteas_p12_p3_scoped_file_contract PROPERTIES TIMEOUT 100)
