# Configurations

# Platform detection
PLATFORM = Linux

ifeq ($(OS), Windows_NT)
	#WINDOWS USE THESE DEFINITIONS
	RM = -rm -f
	SLASH = \\
	SWALLOW_OUTPUT = >nul 2>nul

	TOOLCHAIN = 
	TOOL = 

else
	#LINUX USE THESE DEFINITIONS
	RM = -rm -f
	SLASH = /
	SWALLOW_OUTPUT =
	TOOLCHAIN = 
	TOOL = 
endif 

# Target configuration
ifeq ($(TARGET), 1)

	OUT_TARGET = lib6E5C5B7C979F40108F7CDC08EADFB777.a
	BASE_TARGET = Static
	CCFLAGS_TARGET = -Wall -DECO_LINUX -DECO_LIB -DUGUID_UTILITY
	LDFLAGS_TARGET = 

else

	OUT_TARGET = 6E5C5B7C979F40108F7CDC08EADFB777.so
	BASE_TARGET = Dynamic
	CCFLAGS_TARGET = -Wall -fPIC -DECO_LINUX -DECO_DLL -DUGUID_UTILITY
	LDFLAGS_TARGET = -shared

endif

# Debug symbols configuration
ifeq ($(DEBUG), 1)
	CONFIG_TARGET = $(BASE_TARGET)Debug
else
	CONFIG_TARGET = $(BASE_TARGET)Release
endif

# Architecture selection
ifeq ($(ARCH), x86_16)
	CCFLAGS_TARGET +=
	LDFLAGS_TARGET +=
	ARCH_TARGET = x86_16
else ifeq ($(ARCH), x86)

	CCFLAGS_TARGET +=
	LDFLAGS_TARGET +=

	ARCH_TARGET = x86
else ifeq ($(ARCH), x64)

	CCFLAGS_TARGET +=
	LDFLAGS_TARGET +=

	ARCH_TARGET = amd64
else ifeq ($(ARCH), arm)
    CCFLAGS_TARGET +=   
    LDFLAGS_TARGET += 
    ARCH_TARGET = arm
else ifeq ($(ARCH), aarch32)
	CCFLAGS_TARGET +=   
	LDFLAGS_TARGET += 
	ARCH_TARGET = armv7

	TOOL = $(ECO_TOOLCHAIN)$(SLASH)xpack-arm-none-eabi-gcc-13.2.1-1.1$(SLASH)bin$(SLASH)arm-none-eabi-

else ifeq ($(ARCH), aarch64)
	CCFLAGS_TARGET +=   
	LDFLAGS_TARGET += 
	ARCH_TARGET = armv8

	TOOL = $(ECO_TOOLCHAIN)$(SLASH)xpack-aarch64-none-elf-gcc-13.2.1-1.1$(SLASH)bin$(SLASH)aarch64-none-elf-

else ifeq ($(ARCH), rv32)
	CCFLAGS_TARGET +=   
	LDFLAGS_TARGET += 
	ARCH_TARGET = rv32

	TOOL = $(ECO_TOOLCHAIN)$(SLASH)xpack-riscv-none-elf-gcc-13.2.0-2$(SLASH)bin$(SLASH)riscv-none-elf-

else ifeq ($(ARCH), rv64)
	CCFLAGS_TARGET +=   
	LDFLAGS_TARGET += 
	ARCH_TARGET = rv64gcv

	TOOL = $(ECO_TOOLCHAIN)$(SLASH)xpack-riscv-none-elf-gcc-13.2.0-2$(SLASH)bin$(SLASH)riscv-none-elf-

else ifeq ($(ARCH), mips)
    CCFLAGS_TARGET +=   
    LDFLAGS_TARGET += 
    ARCH_TARGET = mips
else ifeq ($(ARCH), mips64)
    CCFLAGS_TARGET +=   
    LDFLAGS_TARGET += 
    ARCH_TARGET = mips64
endif

# Device selection
ifdef DEVICE
    DEVICE_TARGET = $(DEVICE)$(SLASH)
endif

# Include directories
INC = \
/I ..$(SLASH)..$(SLASH)..$(SLASH)HeaderFiles \
/I ..$(SLASH)..$(SLASH)..$(SLASH)SharedFiles \
/I "$(ECO_FRAMEWORK)$(SLASH)Eco.Core1$(SLASH)SharedFiles" \
/I "$(ECO_FRAMEWORK)$(SLASH)Eco.System1$(SLASH)SharedFiles" \
/I "$(ECO_FRAMEWORK)$(SLASH)Eco.InterfaceBus1$(SLASH)SharedFiles" \
/I "$(ECO_FRAMEWORK)$(SLASH)Eco.MemoryManager1$(SLASH)SharedFiles" \
/I "$(ECO_FRAMEWORK)$(SLASH)Eco.FileSystemManagement1$(SLASH)SharedFiles" 

# Source files.
SRC = \
..$(SLASH)..$(SLASH)..$(SLASH)SourceFiles$(SLASH)CEcoAIEngine1.c \
..$(SLASH)..$(SLASH)..$(SLASH)SourceFiles$(SLASH)CEcoAIEngine1Factory.c

# Libraries

LIBS = -lc -lm -lgcc


# Object files
OBJ = $(SRC:.c=.o)

OUT = $(OUT_TARGET)
OUT_DIR = ..$(SLASH)..$(SLASH)..$(SLASH)BuildFiles$(SLASH)$(PLATFORM)$(SLASH)$(ARCH_TARGET)$(SLASH)$(DEVICE_TARGET)$(CONFIG_TARGET)

# C/C++ compiler flags
CCFLAGS = $(CCFLAGS_TARGET)
 
 # Compile flags
LDFLAGS = $(LDFLAGS_TARGET)

# Tools

CC = $(TOOL)gcc
AR = $(TOOL)gcc-ar
OC = $(TOOL)objcopy



ifeq ($(TARGET), 1)
	CMD_TARGET=$(AR) rcs $(OUT_DIR)$(SLASH)$(OUT) $(OBJ) $(LDFLAGS)
else
	CMD_TARGET=$(CC) -o $(LIBS) $(OUT_DIR)$(SLASH)$(OUT) $(OBJ) $(LDFLAGS)
endif

 
.SUFFIXES: .c

all:  $(OUT)

.c.o:
	mkdir -p "$(subst /,\,$(OUT_DIR))"

	$(GNU)$(CC) $(INC) $(CCFLAGS) -c $< -o $@

 
$(OUT): $(OBJ)
	$(CMD_TARGET)
	$(RM) $(OBJ)

clean:

	$(RM) $(OBJ) $(OUT_DIR)$(SLASH)$(OUT)

