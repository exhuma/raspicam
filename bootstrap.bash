#!/bin/bash

set -e

sntp -s time.google.com

aptitude update
aptitude -y upgrade
aptitude install -y \
    build-essential \
    cheese \
    cmake \
    fluxbox \
    gfortran \
    git \
    libatlas-base-dev \
    libavcodec-dev \
    libavformat-dev \
    libdc1394-22-dev \
    libgtk2.0-dev \
    libjasper-dev \
    libjpeg-dev \
    libjpeg-dev \
    libpng-dev \
    libpng12-dev \
    libswscale-dev \
    libtbb-dev \
    libtbb2 \
    libtiff-dev \
    libtiff5-dev \
    libv4l-dev \
    libx264-dev \
    libxvidcore-dev \
    pkg-config \
    python3-dev \
    python3-numpy \
    python3-pip \
    tmux \
    vim-nox \
    vnc4server

cd
git clone https://github.com/opencv/opencv.git
git clone https://github.com/opencv/opencv_contrib.git

cd ~/opencv
mkdir build
cd build/
cmake \
    -D CMAKE_BUILD_TYPE=Release \
    -D CMAKE_INSTALL_PREFIX=/usr/local \
    -D INSTALL_C_EXAMPLES=OFF \
    -D INSTALL_PYTHON_EXAMPLES=ON \
    -D OPENCV_EXTRA_MODULES_PATH=~/opencv_contrib/modules \
    -D PYTHON3_EXECUTABLE=/usr/bin/python3 \
    -D PYTHON_INCLUDE_DIR=/usr/include/python3.4m \
    -D PYTHON_INCLUDE_DIR2=/usr/include/arm-linux-gnueabihf/python3.4m \
    -D PYTHON_LIBRARY=/usr/lib/arm-linux-gnueabihf/libpython3.4m.so \
    -D PYTHON3_NUMPY_INCLUDE_DIRS=/usr/lib/python3/dist-packages/numpy/core/include \
    -D BUILD_EXAMPLES=ON ../

make -j4
make install

ldconfig  # is this really needed?