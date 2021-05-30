mkdir -p build
cd build
cmake -L .. ${{ matrix.cmake }} ${{ env.ccache_cmake }}
