mkdir -p build
cd build
CC=${{ env.cc }} CXX=${{ env.cxx }} CUDAHOSTCXX=${{ env.cxx }} \
cmake -L .. ${{ env.cmake }}
