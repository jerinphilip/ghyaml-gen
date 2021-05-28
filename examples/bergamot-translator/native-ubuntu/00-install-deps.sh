sudo apt-get update
sudo apt-get install -y \
  libgoogle-perftools-dev libprotobuf-dev protobuf-compiler \
  libboost-all-dev ${{ env.cc }} ${{ env.cxx }} ccache
