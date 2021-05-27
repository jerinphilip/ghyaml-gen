wget -qO- "https://apt.repos.intel.com/intel-gpg-keys/GPG-PUB-KEY-INTEL-SW-PRODUCTS-2019.PUB" | sudo apt-key add -
sudo sh -c "echo deb https://apt.repos.intel.com/mkl all main > /etc/apt/sources.list.d/intel-mkl.list"
sudo apt-get update -o Dir::Etc::sourcelist="/etc/apt/sources.list.d/intel-mkl.list"
sudo apt-get install -y --no-install-recommends intel-mkl-64bit-2020.0-088
