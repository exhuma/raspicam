#!/bin/bash

set -e

if [[ "$(lsb_release -r | cut -f 2)" == "8.0" ]]; then
	sntp -s time.google.com
elif [[ "$(lsb_release -r | cut -f 2)" == "9.1" ]]; then
	timedatectl set-ntp true
else
	echo "This is currently only tested with Raspian 8.0 (jessie) and 9.1 (stretch)"
	exit 1
fi

aptitude update
aptitude -y upgrade
aptitude install -y \
    build-essential \
    cmake \
    gfortran \
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
    python3-venv \
    python3-pip

sudo pip3 install flask picamera

# Some stuff for development (not really needed for the project)
aptitude install -y \
    git \
    tmux \
    vim-nox

cd
git clone https://github.com/opencv/opencv.git
git clone https://github.com/opencv/opencv_contrib.git

cd ~/opencv
mkdir build
cd build/

#
# cmake needs some fairly specific path configurations. It should be possible
# to parse this from "python3-config" but I was too lazy to do
# string-processing in bash. So it's hard-coded for now!
#
if [[ "$(lsb_release -r | cut -f 2)" == "8.0" ]]; then
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
elif [[ "$(lsb_release -r | cut -f 2)" == "9.1" ]]; then
	cmake \
	    -D CMAKE_BUILD_TYPE=Release \
	    -D CMAKE_INSTALL_PREFIX=/usr/local \
	    -D INSTALL_C_EXAMPLES=OFF \
	    -D INSTALL_PYTHON_EXAMPLES=ON \
	    -D OPENCV_EXTRA_MODULES_PATH=~/opencv_contrib/modules \
	    -D PYTHON3_EXECUTABLE=/usr/bin/python3 \
	    -D PYTHON_INCLUDE_DIR=/usr/include/python3.5m \
	    -D PYTHON_INCLUDE_DIR2=/usr/include/arm-linux-gnueabihf/python3.5m \
	    -D PYTHON_LIBRARY=/usr/lib/arm-linux-gnueabihf/libpython3.5m.so \
	    -D PYTHON3_NUMPY_INCLUDE_DIRS=/usr/lib/python3/dist-packages/numpy/core/include \
	    -D BUILD_EXAMPLES=ON ../
else
	echo "This is currently only tested with Raspian 8.0 (jessie)"
	exit 1
fi

make -j4
make install

ldconfig  # is this really needed?
