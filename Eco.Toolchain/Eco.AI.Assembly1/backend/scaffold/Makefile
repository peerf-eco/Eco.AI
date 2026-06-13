# EcoOS Linux static-link template — proven flags (validated 2026-06-01).
# Lives in src/; components are pulled into the project root (one level up).
CC      := gcc
CFLAGS  := -DECO_LIB -DECO_LINUX -DECO_X86_64 -O2

# Every pulled DK package exposes headers in <Pkg>/SharedFiles
INCS    := $(addprefix -I,$(wildcard ../*/SharedFiles))

# Static libs: file name == lib<UGUID>.a. Eco.System1 (…53595333.a) carries
# the real main() and MUST be linked first.
LIBS_ALL := $(wildcard ../*/BuildFiles/Linux/x86_64/StaticRelease/*.a)
LIB_SYS  := $(filter %53595333.a,$(LIBS_ALL))
LIBS     := $(LIB_SYS) $(filter-out $(LIB_SYS),$(LIBS_ALL))

SRCS    := $(wildcard *.c)
BIN     := app

$(BIN): $(SRCS)
	$(CC) $(CFLAGS) $(INCS) -o $@ $(SRCS) $(LIBS) -lm

clean:
	rm -f $(BIN)
