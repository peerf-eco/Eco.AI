call make clean -f Makefile TARGET=0 DEBUG=0 ARCH=x86
call make -f Makefile TARGET=0 DEBUG=0 ARCH=x86
call make clean -f Makefile TARGET=0 DEBUG=1 ARCH=x86
call make -f Makefile TARGET=0 DEBUG=1 ARCH=x86
call make clean -f Makefile TARGET=1 DEBUG=0 ARCH=x86
call make -f Makefile TARGET=1 DEBUG=0 ARCH=x86
call make clean -f Makefile TARGET=1 DEBUG=1 ARCH=x86
call make -f Makefile TARGET=1 DEBUG=1 ARCH=x86
call make clean -f Makefile TARGET=0 DEBUG=0 ARCH=x64
call make -f Makefile TARGET=0 DEBUG=0 ARCH=x64
call make clean -f Makefile TARGET=0 DEBUG=1 ARCH=x64
call make -f Makefile TARGET=0 DEBUG=1 ARCH=x64
call make clean -f Makefile TARGET=1 DEBUG=0 ARCH=x64
call make -f Makefile TARGET=1 DEBUG=0 ARCH=x64
call make clean -f Makefile TARGET=1 DEBUG=1 ARCH=x64
call make -f Makefile TARGET=1 DEBUG=1 ARCH=x64

call make clean -f MakefileExe TARGET=0 DEBUG=0 ARCH=x86
call make -f MakefileExe TARGET=0 DEBUG=0 ARCH=x86
call make clean -f MakefileExe TARGET=0 DEBUG=1 ARCH=x86
call make -f MakefileExe TARGET=0 DEBUG=1 ARCH=x86
call make clean -f MakefileExe TARGET=1 DEBUG=0 ARCH=x86
call make -f MakefileExe TARGET=1 DEBUG=0 ARCH=x86
call make clean -f MakefileExe TARGET=1 DEBUG=1 ARCH=x86
call make -f MakefileExe TARGET=1 DEBUG=1 ARCH=x86
call make clean -f MakefileExe TARGET=0 DEBUG=0 ARCH=x64
call make -f MakefileExe TARGET=0 DEBUG=0 ARCH=x64
call make clean -f MakefileExe TARGET=0 DEBUG=1 ARCH=x64
call make -f MakefileExe TARGET=0 DEBUG=1 ARCH=x64
call make clean -f MakefileExe TARGET=1 DEBUG=0 ARCH=x64
call make -f MakefileExe TARGET=1 DEBUG=0 ARCH=x64
call make clean -f MakefileExe TARGET=1 DEBUG=1 ARCH=x64
call make -f MakefileExe TARGET=1 DEBUG=1 ARCH=x64

pause
