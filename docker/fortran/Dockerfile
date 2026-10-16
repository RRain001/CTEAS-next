FROM debian:12

RUN apt-get update && apt-get install -y \
    gfortran \
    make \
    bash \
    file \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /work
