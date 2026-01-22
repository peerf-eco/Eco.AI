# Configurations

# Platform detection
PLATFORM = Windows

ifeq ($(OS), Windows_NT)
	#WINDOWS USE THESE DEFINITIONS
	RM = -rm -f
	SLASH = \\
	SWALLOW_OUTPUT = >nul 2>nul

	TOOLCHAIN = 
	TOOL = 
	VCVARS = $(MSVS_BT_ROOT)\\VC\\Auxiliary\\Build\\vcvarsall.bat
	MSSDK = $(MSSDK_ROOT)

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

	OUT_TARGET = 6CFEE7807C744D9BA4FFA3F1E6599735.lib
	BASE_TARGET = Static
    CCFLAGS_TARGET = /Gz /TC /W4 /Zc:__cplusplus /D_CRT_SECURE_NO_WARNINGS
    CCFLAGS_TARGET += /D__STDC_VERSION__=199901L /DECO_MEM_EXT /DECO_FILE_EXT /DECO_NET_EXT /DECO_WINDOWS /DECO_LIB
    LDFLAGS_TARGET = /NOLOGO /SUBSYSTEM:CONSOLE /INCREMENTAL:NO

else

	OUT_TARGET = 6CFEE7807C744D9BA4FFA3F1E6599735.dll
	BASE_TARGET = Dynamic
    CCFLAGS_TARGET = /Gz /TC /W4 /Zc:__cplusplus /D_CRT_SECURE_NO_WARNINGS
    CCFLAGS_TARGET += /D__STDC_VERSION__=199901L /DECO_MEM_EXT /DECO_FILE_EXT /DECO_NET_EXT /DECO_WINDOWS /DECO_DLL
    LDFLAGS_TARGET = /NOLOGO /SUBSYSTEM:CONSOLE /INCREMENTAL:NO

endif

# Debug symbols configuration
ifeq ($(DEBUG), 1)
	CONFIG_TARGET = $(BASE_TARGET)Debug

    CCFLAGS_TARGET += /D_DEBUG /Zi /Fd$(subst /,$(SLASH),$(OUT_DIR)/$(OUT_TARGET:.lib=.pdb))
    LDFLAGS_TARGET += 
    ifeq ($(TARGET), 1)
        CCFLAGS_TARGET += /MTd
    else
        LDFLAGS_TARGET += /PDB:$(subst /,$(SLASH),$(OUT_DIR)/$(OUT_TARGET:.dll=.pdb))
    endif

else
	CONFIG_TARGET = $(BASE_TARGET)Release

    CCFLAGS_TARGET += /DNDEBUG /Z7
    ifeq ($(TARGET), 1)
        CCFLAGS_TARGET += /MT
    endif
    LDFLAGS_TARGET += /DEBUG:NONE

endif

# Architecture selection
ifeq ($(ARCH), x86_16)
	CCFLAGS_TARGET +=
	LDFLAGS_TARGET +=
	ARCH_TARGET = x86_16
else ifeq ($(ARCH), x86)

	CCFLAGS_TARGET += /DECO_X86_32
	LDFLAGS_TARGET += /MACHINE:X86

	ARCH_TARGET = x86
else ifeq ($(ARCH), x64)

	CCFLAGS_TARGET += /DECO_X86_64  
	LDFLAGS_TARGET += /MACHINE:X64

	ARCH_TARGET = amd64
else ifeq ($(ARCH), arm)
    CCFLAGS_TARGET +=   
    LDFLAGS_TARGET += 
    ARCH_TARGET = arm
else ifeq ($(ARCH), aarch32)
	CCFLAGS_TARGET +=   
	LDFLAGS_TARGET += 
	ARCH_TARGET = armv7
else ifeq ($(ARCH), aarch64)
	CCFLAGS_TARGET +=   
	LDFLAGS_TARGET += 
	ARCH_TARGET = armv8
else ifeq ($(ARCH), rv32)
	CCFLAGS_TARGET +=   
	LDFLAGS_TARGET += 
	ARCH_TARGET = rv32
else ifeq ($(ARCH), rv64)
	CCFLAGS_TARGET +=   
	LDFLAGS_TARGET += 
	ARCH_TARGET = rv64gcv
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
..$(SLASH)..$(SLASH)..$(SLASH)SourceFiles$(SLASH)CEcoONNX1.c \
..$(SLASH)..$(SLASH)..$(SLASH)SourceFiles$(SLASH)CEcoONNX1Factory.c

# Libraries

LIBS = "kernel32.lib" "user32.lib" "gdi32.lib" "winspool.lib" "comdlg32.lib" "advapi32.lib" "shell32.lib" "ole32.lib" "oleaut32.lib" "uuid.lib" "odbc32.lib" "odbccp32.lib"


# Object files
OBJ = $(SRC:.c=.o)

OUT = $(OUT_TARGET)
OUT_DIR = ..$(SLASH)..$(SLASH)..$(SLASH)BuildFiles$(SLASH)$(PLATFORM)$(SLASH)$(ARCH_TARGET)$(SLASH)$(DEVICE_TARGET)$(CONFIG_TARGET)

# C/C++ compiler flags
CCFLAGS = $(CCFLAGS_TARGET)
 
 # Compile flags
LDFLAGS = $(LDFLAGS_TARGET)

# Tools

CC = cmd /c "$(VCVARS) $(ARCH) > nul && cl"
LD = cmd /c "$(VCVARS) $(ARCH) > nul && link"
AR = cmd /c "$(VCVARS) $(ARCH) > nul && lib"



ifeq ($(TARGET), 1)
	CMD_TARGET=$(AR) /OUT:$(OUT_DIR)$(SLASH)$(OUT) $(OBJ) $(LDFLAGS)
else
	CMD_TARGET=$(LD) /DLL $(LIBS) /OUT:$(OUT_DIR)$(SLASH)$(OUT) $(OBJ) $(LDFLAGS)
endif

 
.SUFFIXES: .c

all:  $(OUT)

.c.o:
	mkdir -p "$(subst /,\,$(OUT_DIR))"

	$(CC) $(INC) $(CCFLAGS) /c $< /Fo$@

 
$(OUT): $(OBJ)
	$(CMD_TARGET)
	$(RM) $(OBJ)

clean:

	$(RM) $(OBJ) $(OUT_DIR)$(SLASH)$(OUT) $(OUT_DIR)$(SLASH)*.pdb $(OUT_DIR)$(SLASH)*.ilk

