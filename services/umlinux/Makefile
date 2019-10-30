VERSION := 4.19.45

umlinux : linux-$(VERSION)/.config
	$(Q)$(MAKE) ARCH=um -j2 -C linux-$(VERSION)
	ln -sf linux-$(VERSION)/linux linux

linux-$(VERSION).tar.xz :
	curl https://cdn.kernel.org/pub/linux/kernel/v4.x/linux-$(VERSION).tar.xz --output linux-$(VERSION).tar.xz

linux-$(VERSION): linux-$(VERSION).tar.xz
	tar -xf linux-$(VERSION).tar.xz
	touch .stamp_extract

.stamp_patched : | linux-$(VERSION)
	for p in patches/*.patch ; do \
		patch -g0 -p1 -E -d linux-$(VERSION) -t -N < $$p; \
	done
	touch .stamp_patched

linux-$(VERSION)/.config : | .stamp_patched
	cp defconfig linux-$(VERSION)/.config

clean :
	$(Q)$(MAKE) ARCH=um -C linux-$(VERSION) clean

mrproper :
	rm -rf linux-$(VERSION)
	rm -rf linux-$(VERSION).tar.xz
	rm .stamp*

.PHONY: umlinux clean mrproper
