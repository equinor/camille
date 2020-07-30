cmake_minimum_required(VERSION 3.11.0)
project(camille-native LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_VISIBILITY_PRESET "hidden")
set(CMAKE_C_VISIBILITY_PRESET   "hidden")

find_package(PythonExtensions REQUIRED)

add_library(core MODULE camille/core.cpp)
target_include_directories(core
    PRIVATE
        ${PYBIND11_INCLUDE_DIRS}
)
python_extension_module(core)

if (MSVC)
    target_compile_options(core
        BEFORE
        PRIVATE
            /EHsc
    )
endif ()

install(TARGETS core LIBRARY DESTINATION camille)
