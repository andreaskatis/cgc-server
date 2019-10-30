#!/bin/bash

repo_root=$(dirname $(readlink -f $0))
#git -C $repo_root submodule update --init --recursive 
docker build -t cgcserv $repo_root
