# From https://ngc.nvidia.com/catalog/containers/nvidia:l4t-pytorch it contains Pytorch v1.5 and torchvision v0.6.0
FROM nvcr.io/nvidia/l4t-pytorch:r32.4.3-pth1.6-py3

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get -y update && apt-get -y upgrade
RUN apt-get install -y wget python3-setuptools python3-pip libfreetype6-dev

### Install OpenCV 4.1.0 ###
RUN apt-get -y install qt5-default
COPY ./OpenCV-4.1.1-dirty-aarch64.sh .
RUN ./OpenCV-4.1.1-dirty-aarch64.sh --prefix=/usr/local/ --skip-license && ldconfig

RUN apt-get update && apt-get install -y --no-install-recommends \
	python3-pip \
	python3-dev


# Install LibRealSense from source
RUN git clone https://github.com/IntelRealSense/librealsense.git
## Install the core packages required to build librealsense libs
RUN apt-get install -y git libssl-dev libusb-1.0-0-dev pkg-config libgtk-3-dev
### Distribution-specific packages for Ubuntu 18
RUN apt-get install -y libglfw3-dev libgl1-mesa-dev libglu1-mesa-dev
### Run Intel Realsense permissions script
RUN pwd
WORKDIR ./librealsense
RUN pwd
RUN ls ./config
# Make sure that your RealSense cameras are disconnected at this point
# RUN ./scripts/setup_udev_rules.sh
RUN cp ./config/99-realsense-libusb.rules /etc/udev/rules.d/
RUN apt-get install -y udev
RUN udevadm control --reload-rules
RUN udevadm trigger
# Now starting the build
RUN mkdir build && cd build
## CMake with Python bindings
## see link: https://github.com/IntelRealSense/librealsense/tree/master/wrappers/python#building-from-source
RUN cmake ../ -DBUILD_PYTHON_BINDINGS:bool=true
## Recompile and install librealsense binaries
RUN make uninstall && make clean && make -j6 && make install
RUN export PYTHONPATH=$PYTHONPATH:/usr/local/lib/python3.6/pyrealsense2
