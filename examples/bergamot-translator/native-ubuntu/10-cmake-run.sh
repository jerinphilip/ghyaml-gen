mkdir -p build
cd build
CC=/usr/bin/gcc-${{ env.gcc }} CXX=/usr/bin/g++-${{ env.gcc }} CUDAHOSTCXX=/usr/bin/g++-${{ env.gcc }} \
cmake -L .. \
  $${{ env.cmake }}
