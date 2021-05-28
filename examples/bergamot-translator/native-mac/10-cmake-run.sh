mkdir -p build
cd build
cmake -L .. ${{ env.cmake }}
