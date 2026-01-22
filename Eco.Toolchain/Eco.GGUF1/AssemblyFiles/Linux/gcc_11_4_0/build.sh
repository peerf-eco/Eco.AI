#!/usr/bin/env bash
echo "Build Eco.GGUF1"
DIR=$(cd "$(dirname "$0")"; pwd)
echo $DIR
# ARCH=x64 | ARCH=rv64 | ARCH=arm64
# ARCH_EXT= | ARCH_EXT=gcv | ARCH_EXT=-v8a
make clean -f Makefile TARGET=0 DEBUG=0 ARCH=x64
make -f Makefile TARGET=0 DEBUG=0 ARCH=x64
make clean -f Makefile TARGET=0 DEBUG=1 ARCH=x64
make -f Makefile TARGET=0 DEBUG=1 ARCH=x64
make clean -f Makefile TARGET=1 DEBUG=0 ARCH=x64
make -f Makefile TARGET=1 DEBUG=0 ARCH=x64
make clean -f Makefile TARGET=1 DEBUG=1 ARCH=x64
make -f Makefile TARGET=1 DEBUG=1 ARCH=x64

make clean -f MakefileExe TARGET=0 DEBUG=0 ARCH=x64
make -f MakefileExe TARGET=0 DEBUG=0 ARCH=x64
make clean -f MakefileExe TARGET=0 DEBUG=1 ARCH=x64
make -f MakefileExe TARGET=0 DEBUG=1 ARCH=x64
make clean -f MakefileExe TARGET=1 DEBUG=0 ARCH=x64
make -f MakefileExe TARGET=1 DEBUG=0 ARCH=x64
make clean -f MakefileExe TARGET=1 DEBUG=1 ARCH=x64
make -f MakefileExe TARGET=1 DEBUG=1 ARCH=x64
