#!/bin/bash
sudo apt-get install make unrar-free autoconf automake libtool gcc g++ gperf flex bison texinfo gawk ncurses-dev libexpat-dev python-dev python python-serial sed git unzip bash help2man wget bzip2 libtool-bin
git clone --recursive https://github.com/pfalcon/esp-open-sdk.git
mv esp-open-sdk/ ~/.esp-open-sdk/
cd ~/.esp-open-sdk/
make toolchain esptool libhal STANDALONE=n
echo "export PATH=$PATH:$(pwd)/xtensa-lx106-elf/bin" >> ~/.bashrc
source ~/.bashrc