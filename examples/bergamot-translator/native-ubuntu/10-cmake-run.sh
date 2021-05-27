mkdir -p build
cd build
CC=/usr/bin/gcc-${{ matrix.gcc }} CXX=/usr/bin/g++-${{ matrix.gcc }} CUDAHOSTCXX=/usr/bin/g++-${{ matrix.gcc }} \
cmake -L .. \
  -DCMAKE_BUILD_TYPE=${{ matrix.cmake.CMAKE_BUILD_TYPE }}\
  -DCOMPILE_TESTS=${{ matrix.cmake.COMPILE_TESTS }}\
  -DCOMPILE_EXAMPLES=${{ matrix.cmake.COMPILE_EXAMPLES }} \
  -DCOMPILE_SERVER=${{ matrix.cmake.COMPILE_SERVER }} \
  -DUSE_WASM_COMPATIBLE_SOURCE=${{ matrix.cmake.USE_WASM_COMPATIBLE_SOURCE }} \
  -DCMAKE_C_COMPILER_LAUNCHER=${{ matrix.cmake.CMAKE_C_COMPILER_LAUNCHER}} \
  -DCMAKE_CXX_COMPILER_LAUNCHER=${{ matrix.cmake.CMAKE_CXX_COMPILER_LAUNCHER}} 

