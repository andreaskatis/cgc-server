FROM ubuntu:18.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get upgrade -y

RUN \
	apt-get update && \
	apt-get install -y \
	libc6-dev \
	libc6-dev-i386 \
	gcc-multilib \
	g++-multilib \
	python \
	clang \
	python-pip \
	cmake \
	git \
	vim \
	pandoc \
	net-tools \
	netcat \
	iputils-ping \
	gdb \
	python3 \
	lcov \
	python3-pip \
	libnl-3-dev \
	libnl-genl-3-dev \
	slirp \
	uml-utilities \
	bridge-utils \
	bc \
	pkg-config \
	libssl-dev \
	libnl-3-dev \
	libnl-genl-3-dev \
	wpasupplicant \
	curl \
	bison \
	flex \
	unzip

RUN \
	pip3 install \
	gcovr \
	Flask==1.0.2 \
	flask_socketio==3.3.2 \
	gdbgui \
	python_ptrace \
	inotify \
	scapy>=2.4.3
# scapy must be either 2.4.0 or >=2.4.3 due to https://github.com/secdev/scapy/issues/1783

#needed for cgc build
RUN pip install xlsxwriter pycrypto

COPY . /root/cgc
EXPOSE 5000-5100

WORKDIR /root/cgc

RUN make -C /root/cgc/gcovrt all install

ENV FLASK_DEBUG=0
ENTRYPOINT [ "python3", "/root/cgc/cgcserv/__main__.py"]

