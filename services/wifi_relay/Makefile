CFLAGS := -Wall

all: wifi_relay hostapd umlinux

../umlinux/linux:
	make -C ../umlinux

../hostapd/hostapd:
	make -C ../hostapd

hostapd: ../hostapd/hostapd

umlinux: ../umlinux/linux

mrpropper: clean

clean:
	rm relay

wifi_relay: relay

.PHONY: wifi_relay
