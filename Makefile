IMAGE   := face-unlock-build
DOCKER  := docker run --rm --tmpfs /build:mode=1777 --user "$$(id -u):$$(id -g)" -e HOME=/tmp -w /build/src -v "$(CURDIR)":/build/src $(IMAGE)
VERSION := $(shell dpkg-parsechangelog -S Version 2>/dev/null)
DEB     := dist/face-unlock_$(VERSION)_amd64.deb
# Custom release artifact name (e.g. `make release DEB_NAME=face-unlock-v1.0.0`)
DEB_NAME ?= face-unlock_$(VERSION)_amd64
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

install: $(DEB)
	sudo apt install ./$(DEB)

uninstall:
	sudo apt remove face-unlock

## Build a release artifact with a custom filename (defaults to face-unlock_<version>_amd64.deb)
## Example: make release DEB_NAME=face-unlock-v1.0.0
release: deb-host
	@if [ "$(DEB_NAME).deb" != "$(DEB)" ] && [ -f "$(DEB)" ]; then \
		cp "$(DEB)" "$(RELEASE_DEB)"; \
		echo "==> Release artifact: $(RELEASE_DEB)"; \
	else \
		echo "==> Release artifact: $(DEB) (use DEB_NAME= to rename)"; \
	fi

clean:
	rm -rf dist debian/build debian/face-unlock debian/.debhelper debian/debhelper-build-stamp \
		debian/files debian/*.substvars debian/*.debhelper.log
	find src tests -name __pycache__ -prune -exec rm -rf {} +

## Also remove downloaded sources and the compiled dlib wheel
distclean: clean
	rm -rf vendor/*.tar.gz vendor/*.bz2 vendor/wheels
