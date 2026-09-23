# Clean build environment for the face-unlock package.
# The image only holds build tools; the source tree is bind-mounted at /build/src.
FROM ubuntu:26.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential debhelper devscripts fakeroot lintian \
        meson ninja-build cmake pkg-config \
        python3 python3-dev python3-pip python3-setuptools python3-wheel \
        python3-numpy python3-opencv python3-gi \
        libpam0g-dev libinih-dev libevdev-dev libopenblas-dev liblapack-dev \
        bzip2 ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

# dpkg-buildpackage writes its results to the parent of the source tree
RUN mkdir -p /build && chmod 1777 /build
WORKDIR /build/src
