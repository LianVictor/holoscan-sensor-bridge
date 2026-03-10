# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

if(NOT DEFINED ARCH)
  set(ARCH "${CMAKE_SYSTEM_PROCESSOR}")
endif()
if(NOT ARCH STREQUAL "x86_64" AND NOT ARCH STREQUAL "aarch64")
  message(FATAL_ERROR "DOCA is only supported on x86_64 and aarch64; ARCH is \"${ARCH}\".")
endif()

find_package(PkgConfig REQUIRED)
find_package(CUDAToolkit REQUIRED) # Or check for CMAKE_CUDA_COMPILER
find_library(MLX5_LIB mlx5 REQUIRED)
find_package(ibverbs REQUIRED)
SET(ENV{PKG_CONFIG_PATH} "$ENV{PKG_CONFIG_PATH}:/opt/mellanox/dpdk/lib/${ARCH}-linux-gnu/pkgconfig:/opt/mellanox/doca/lib/${ARCH}-linux-gnu/pkgconfig:/opt/mellanox/collectx/lib/${ARCH}-linux-gnu/pkgconfig")
SET(DOCA_PATH /opt/mellanox/doca)
pkg_search_module(DOCA_GPUNETIO REQUIRED doca-gpunetio)
pkg_search_module(DOCA_VERBS REQUIRED doca-verbs)

enable_language(CUDA)

set(LOCAL_CUDA_ARCHS "")
# Use standard CMAKE_CUDA_ARCHITECTURES when set (e.g. -D from Docker or parent)
if(DEFINED CMAKE_CUDA_ARCHITECTURES AND NOT CMAKE_CUDA_ARCHITECTURES STREQUAL "")
  if(CMAKE_CUDA_ARCHITECTURES MATCHES ";")
    set(LOCAL_CUDA_ARCHS "${CMAKE_CUDA_ARCHITECTURES}")
  else()
    separate_arguments(LOCAL_CUDA_ARCHS NATIVE_COMMAND "${CMAKE_CUDA_ARCHITECTURES}")
  endif()
else()
  find_program(NVIDIA_SMI_EXECUTABLE nvidia-smi)
  if(NVIDIA_SMI_EXECUTABLE)
    execute_process(
      COMMAND ${NVIDIA_SMI_EXECUTABLE}
              --query-gpu=compute_cap
              --format=csv,noheader
      RESULT_VARIABLE CUDA_SMI_RESULT
      OUTPUT_VARIABLE CUDA_CC_LIST_RAW
      OUTPUT_STRIP_TRAILING_WHITESPACE
      ERROR_QUIET
    )
    if(CUDA_SMI_RESULT EQUAL 0 AND NOT CUDA_CC_LIST_RAW STREQUAL "")
      separate_arguments(CUDA_CC_LIST NATIVE_COMMAND "${CUDA_CC_LIST_RAW}")
      foreach(cc IN LISTS CUDA_CC_LIST)
        string(STRIP "${cc}" cc_stripped)
        if(cc_stripped STREQUAL "")
          continue()
        endif()
        string(REPLACE "." "" arch_num "${cc_stripped}")
        list(FIND LOCAL_CUDA_ARCHS "${arch_num}" _idx)
        if(_idx EQUAL -1)
          list(APPEND LOCAL_CUDA_ARCHS "${arch_num}")
        endif()
      endforeach()
    endif()
  endif()

  # Fallback if nvidia-smi not available or returns nothing
  if(LOCAL_CUDA_ARCHS STREQUAL "")
    message(WARNING
            "nvidia-smi not available or no GPU ARCHs passed or reported; "
            "falling back to fixed candidate architectures."
    )
    set(LOCAL_CUDA_ARCHS 80 86 87 90 100 110 120)
  endif()
endif()

# Ask nvcc which architectures it supports and intersect with local GPU archs
execute_process(
  COMMAND ${CMAKE_CUDA_COMPILER} --list-gpu-arch
  OUTPUT_VARIABLE CUDA_ARCH_LIST_RAW
  OUTPUT_STRIP_TRAILING_WHITESPACE
)

set(SUPPORTED_CUDA_ARCHS "")
foreach(arch IN LISTS LOCAL_CUDA_ARCHS)
  string(FIND "${CUDA_ARCH_LIST_RAW}" "compute_${arch}" pos)
  if(NOT pos EQUAL -1)
    list(APPEND SUPPORTED_CUDA_ARCHS "${arch}")
  endif()
endforeach()

if(SUPPORTED_CUDA_ARCHS STREQUAL "")
  message(FATAL_ERROR
          "None of the requested CUDA_ARCHITECTURES (${LOCAL_CUDA_ARCHS}) "
          "are supported by ${CMAKE_CUDA_COMPILER}. "
  )
endif()

# Check if DOCA is available
message(STATUS "DOCA found at ${DOCA_PATH}")
message(STATUS "CUDA ARCHS: ${SUPPORTED_CUDA_ARCHS}")

add_library(gpu_roce_transceiver STATIC
  gpu_roce_transceiver_op.cpp
  gpu_roce_transceiver.cpp
  gpu_roce_transceiver_doca.cpp
  gpu_roce_transceiver_kernel.cu
)

set_property(TARGET gpu_roce_transceiver PROPERTY CUDA_ARCHITECTURES ${SUPPORTED_CUDA_ARCHS})

add_library(hololink::operators::gpu_roce_transceiver ALIAS gpu_roce_transceiver)

include(GNUInstallDirs)
target_include_directories(gpu_roce_transceiver
  PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/../../..>
    $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>
    ${DOCA_GPUNETIO_INCLUDE_DIRS}
    ${DOCA_VERBS_INCLUDE_DIRS}
)

target_compile_options(gpu_roce_transceiver PRIVATE ${DOCA_GPUNETIO_CFLAGS} ${DOCA_VERBS_CFLAGS})

target_link_directories(gpu_roce_transceiver PUBLIC ${DOCA_GPUNETIO_LIBRARY_DIRS} ${DOCA_VERBS_LIBRARY_DIRS})
target_link_libraries(gpu_roce_transceiver
  PUBLIC
    hololink::operators::base_receiver_op
    holoscan::core
  PRIVATE
    CUDA::cuda_driver
    ${DOCA_GPUNETIO_LIBRARIES} -ldoca_gpunetio -ldoca_common
    ${DOCA_VERBS_LIBRARIES}
)

# Suppress deprecated declarations warning for DOCA APIs
target_compile_options(gpu_roce_transceiver PRIVATE -Wno-deprecated-declarations)

# Set RPATH to include DOCA library directories
set_target_properties(gpu_roce_transceiver PROPERTIES
  INSTALL_RPATH "$ORIGIN:${DOCA_GPUNETIO_LIBRARY_DIRS}:${DOCA_VERBS_LIBRARY_DIRS}"
  BUILD_RPATH "${DOCA_GPUNETIO_LIBRARY_DIRS};${DOCA_VERBS_LIBRARY_DIRS}"
)

# Installation of the gpu_roce_transceiver operator
install(TARGETS gpu_roce_transceiver
        DESTINATION ${CMAKE_INSTALL_LIBDIR}
        COMPONENT hololink-roce-operators)

install(FILES ${CMAKE_CURRENT_SOURCE_DIR}/gpu_roce_transceiver_op.hpp
        DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/operators/gpu_roce_transceiver
        COMPONENT hololink-roce-operators)

install(FILES ${CMAKE_CURRENT_SOURCE_DIR}/gpu_roce_transceiver.cuh
        DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/operators/gpu_roce_transceiver
        COMPONENT hololink-roce-operators)

install(FILES ${CMAKE_CURRENT_SOURCE_DIR}/gpu_roce_transceiver_common.hpp
        DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/operators/gpu_roce_transceiver
        COMPONENT hololink-roce-operators)
