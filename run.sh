#!/bin/bash
repo_root=$(dirname $(readlink -f $0))

# Ignore errors from git, Make sure this is patched
git -C $repo_root/cb-multios apply $repo_root/patches/* 2>/dev/null
docker run -it -p 5000-5100:5000-5100 \
	--security-opt seccomp:unconfined \
	--cap-add=SYS_PTRACE \
	-v $repo_root/services:/root/cgc/services \
	cgcserv
