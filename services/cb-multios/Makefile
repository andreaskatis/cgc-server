include cb-multios.mk

VERSION := e50a0301c795c018686973d38ebcc1920f63240a

all: $(cb-multios_provides)

$(cb-multios_provides): .stamp_patched
	VERBOSE=1 CC="$(GCOV_CC)" CXX="$(GCOV_CXX)" CGC_CHALLENGE="$@" cb-multios/build.sh

$(VERSION).zip :
	curl -O -L https://github.com/trailofbits/cb-multios/archive/$(VERSION).zip

cb-multios : $(VERSION).zip
	unzip -uoq $(VERSION).zip
	mv cb-multios-$(VERSION) cb-multios

clean:
	rm -rf cb-multios/build

mrpropper:
	rm -rf cb-multios

.stamp_patched : | cb-multios
	for p in patches/*.patch ; do \
		patch -g0 -p1 -E -d cb-multios -t -N < $$p; \
	done
	touch .stamp_patched

.PHONY: all
