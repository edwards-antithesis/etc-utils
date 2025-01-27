FROM ubuntu:20.04

ENV TZ=America
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
# Update ubuntu
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        software-properties-common \
        curl \
        wget \
        git \
        build-essential \
        binutils-dev \
        cmake \
        gpg-agent \
        gcc-9-plugin-dev \
        python3-dev \
        libpcre3-dev \
        netcat \
        net-tools \
        python3-pip \
        jq \
        vim

# Install golang
RUN add-apt-repository ppa:longsleep/golang-backports
RUN apt-get update && \
	apt-get install -y \
	golang

WORKDIR /git

RUN pip3 install web3 ruamel.yaml

RUN git clone https://github.com/protolambda/eth2-bootnode.git

RUN cd /git/eth2-bootnode && go install .

RUN ln -s /root/go/bin/eth2-bootnode /usr/local/bin/eth2-bootnode

