VERSION := 2.6

PWD := $(shell pwd)
export CC := $(PWD)/../gcov-gcc
export CXX :=  $(PWD)/../gcov-g++

hostapd : hostapd-$(VERSION)/hostapd/.config
	make V=1 -C hostapd-$(VERSION)/hostapd
	ln -sf hostapd-$(VERSION)/hostapd/hostapd hostapd

hostapd-$(VERSION).tar.gz :
	curl https://w1.fi/releases/hostapd-$(VERSION).tar.gz --output hostapd-$(VERSION).tar.gz

.stamp_extract: hostapd-$(VERSION).tar.gz
	tar -xf hostapd-$(VERSION).tar.gz
	touch .stamp_extract

.stamp_patched : | hostapd-$(VERSION)
	for p in patches/*.patch ; do \
		patch -g0 -p1 -E -d hostapd-$(VERSION) -t -N < $$p; \
	done
	touch .stamp_patched

hostapd-$(VERSION)/hostapd/.config: .stamp_extract .stamp_patched
	cp defconfig hostapd-$(VERSION)/hostapd/.config

clean :
	make -C hostapd-$(VERSION)/hostapd clean

mrproper :
	rm -rf hostapd-$(VERSION)
	rm hostapd-$(VERSION).tar.gz

.PHONY: mrproper clean hostapd
