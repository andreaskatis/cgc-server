.PHONY: cgcserv

all: cgcserv

cgcserv:
	docker build -t cgcserv .
