IMAGE   := face-unlock-build
DOCKER  := docker run --rm --tmpfs /build:mode=1777 --user "$$(id -u):$$(id -g)" -e HOME=/tmp -w /build/src -v "$(CURDIR)":/build/src $(IMAGE)
VERSION := $(shell dpkg-parsechangelog -S Version 2>/dev/null)
ARCH    := $(shell dpkg-architecture -qDEB_HOST_ARCH)
DISTRO  := ubuntu$(shell . /etc/os-release && printf %s "$$VERSION_ID")
CONTAINER_DISTRO := $(shell sed -n 's/^FROM ubuntu:/ubuntu/p' packaging/Dockerfile | head -1)
DEB     := dist/face-unlock-$(DISTRO)-$(ARCH)-$(VERSION).deb
# Optional custom release artifact name.
DEB_NAME ?= face-unlock-$(DISTRO)-$(ARCH)-$(VERSION)
RELEASE_DEB := dist/$(DEB_NAME).deb

.PHONY: deb deb-host image test run install uninstall clean distclean release

## Build the .deb in a clean Ubuntu 26.04 container (default)
deb: image
	$(DOCKER) scripts/build-deb.sh

## Build the .deb directly on this machine (needs Build-Depends from debian/control)
deb-host:
	scripts/build-deb.sh

image:
	docker build -q -t $(IMAGE) packaging/

test:
	PYTHONPATH=src python3 -m unittest discover -s tests -v

## Run the app from the source tree (the helper must be installed)
run:
	PYTHONPATH=src python3 -m face_unlock

install: deb
	sudo apt install ./dist/face-unlock-$(CONTAINER_DISTRO)-$(ARCH)-$(VERSION).deb

uninstall:
	sudo apt remove face-unlock

## Build a release artifact with an optional custom filename.
release: deb-host
	@if [ "$(RELEASE_DEB)" != "$(DEB)" ]; then cp "$(DEB)" "$(RELEASE_DEB)"; fi
	@echo "==> Release artifact: $(RELEASE_DEB)"

clean:
	rm -rf dist debian/build debian/face-unlock debian/.debhelper debian/debhelper-build-stamp \
		debian/files debian/*.substvars debian/*.debhelper.log
	find src tests -name __pycache__ -prune -exec rm -rf {} +

## Also remove downloaded sources and the compiled dlib wheel
distclean: clean
	rm -rf vendor/*.tar.gz vendor/*.bz2 vendor/wheels
