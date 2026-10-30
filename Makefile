#############################################################################
#
# Generic Makefile Template for C/C++ Projects
#
# License: GPL (General Public License)
# Note:    GPL only applies to this file; you can use this Makefile in non-GPL projects.
# Author:  Pear <service AT pear DOT hk>
# Date:    2026/10/28 (version 0.8)
# Author:  kevin1078 <kevin1078 AT 126 DOT com>
# Date:    2012/04/24 (version 0.6)
# Author:  whyglinux <whyglinux AT gmail DOT com>
# Date:    2008/04/05 (version 0.5)
#          2007/06/26 (version 0.4)
#          2007/04/09 (version 0.3)
#          2007/03/24 (version 0.2)
#          2006/03/04 (version 0.1)
#===========================================================================

# ---- User configuration ---------------------------------------------------
# Examples:
#   PROGRAM=myapp  TYPE=exe  CFLAGS="-O2 -g"
#   SRCDIRS="src lib"  EXTRA_LIBS="-lm -lz"  EXE_LDFLAGS=-s
#   make TYPE=static | make TYPE=shared | make V=1 | make NODEP=yes
#
# PROGRAM      product base name (default: current directory name)
# TYPE         auto | exe | static | shared
# MAIN_SRCS    explicit entry points; skips the auto scan
# SRCDIRS      source dirs; empty = scan '.' recursively
# INCLUDE      extra -I dirs
# EXTRA_*      extra compile/link flags
# EXE_LDFLAGS  executable-only flags (use -s for a stripped release)
# CROSS_COMPILE  cross-compiler prefix (e.g. arm-none-eabi-)
# NODEP=yes    disable dependency generation
# V=1          print full commands
PROGRAM                ?= $(notdir $(CURDIR))
TYPE                   ?= auto
MAIN_SRCS              ?=
SRCDIRS                ?=
INCLUDE                ?=
EXTRA_CFLAGS           ?= -fdata-sections -ffunction-sections
EXTRA_LDFLAGS          ?=
EXTRA_LIBS             ?=
CPPFLAGS               ?=
CFLAGS                 ?= -O3
CXXFLAGS               ?= -O3
LDFLAGS                ?=
EXE_LDFLAGS            ?=
CROSS_COMPILE          ?=
NODEP                  ?=
V                      ?=
SRCEXTS                ?= .c .C .cc .cpp .CPP .c++ .cxx .cp
HDREXTS                ?= .h .H .hh .hpp .HPP .h++ .hxx .hp
RM                     ?= rm -f
ETAGS                  ?= etags
ETAGSFLAGS             ?=
CTAGS                  ?= ctags
CTAGSFLAGS             ?=
# OS-specific flags (kept from the original template).
EXTRA_CFLAGS_MACOS     ?=
EXTRA_LDFLAGS_MACOS    ?= -Wl,-search_paths_first -Wl,-dead_strip
LDFLAGS_MACOS          ?=
EXTRA_CFLAGS_LINUX     ?=
EXTRA_LDFLAGS_LINUX    ?= -Wl,--gc-sections
LDFLAGS_LINUX          ?=
EXTRA_CFLAGS_WINDOWS   ?=
EXTRA_LDFLAGS_WINDOWS  ?=
LDFLAGS_WINDOWS        ?=

# ---- Platform detection ---------------------------------------------------
ifeq ($(OS),Windows_NT)
  PLATFORM      := Windows
  EXE_SUFFIX    := .exe
  SHARED_PREFIX :=
  SHARED_SUFFIX := .dll
  # cmd.exe also has a built-in echo, so probe a real sh and set SHELL only here.
  ifeq ($(shell sh -c "echo __ok__"),__ok__)
    SHELL := sh.exe
  else
    $(error No POSIX shell found. Install Git for Windows or MSYS2 and put its usr\bin on PATH)
  endif
else
  UNAME_S := $(shell uname -s)
  ifeq ($(UNAME_S),Darwin)
    PLATFORM      := Darwin
    EXE_SUFFIX    :=
    SHARED_PREFIX := lib
    SHARED_SUFFIX := .dylib
  else
    PLATFORM      := Linux
    EXE_SUFFIX    :=
    SHARED_PREFIX := lib
    SHARED_SUFFIX := .so
  endif
endif

ifeq ($(PLATFORM),Darwin)
  EXTRA_CFLAGS  += $(EXTRA_CFLAGS_MACOS)
  EXTRA_LDFLAGS += $(EXTRA_LDFLAGS_MACOS)
  LDFLAGS       += $(LDFLAGS_MACOS)
else ifeq ($(PLATFORM),Linux)
  EXTRA_CFLAGS  += $(EXTRA_CFLAGS_LINUX)
  EXTRA_LDFLAGS += $(EXTRA_LDFLAGS_LINUX)
  LDFLAGS       += $(LDFLAGS_LINUX)
else
  EXTRA_CFLAGS  += $(EXTRA_CFLAGS_WINDOWS)
  EXTRA_LDFLAGS += $(EXTRA_LDFLAGS_WINDOWS)
  LDFLAGS       += $(LDFLAGS_WINDOWS)
endif

# "cc" does not exist on MinGW; only override make's built-in defaults.
ifeq ($(origin CC),default)
  CC  := $(CROSS_COMPILE)gcc
endif
ifeq ($(origin CXX),default)
  CXX := $(CROSS_COMPILE)g++
endif
ifeq ($(origin AR),default)
  AR  := $(CROSS_COMPILE)ar
endif

override CPPFLAGS += $(INCLUDE)
EXTRA_LDFLAGS += $(EXTRA_LIBS)

# ---- Source discovery -----------------------------------------------------
DEPTH_LIMIT := 8
# True only for a real directory; symlinked directories are not followed.
is_real_dir = $(if $(wildcard $1/.),$(if $(filter-out $(abspath $1),$(realpath $1)),,yes),)

rwildcard = $(foreach d,$(wildcard $1*),\
  $(if $(call is_real_dir,$d),\
    $(if $(filter $(DEPTH_LIMIT),$(words $(subst /, ,$d))),\
      $(warning rwildcard: depth limit ($(DEPTH_LIMIT)) reached at '$d'; deeper files are ignored),\
      $(call rwildcard,$d/,$2)))\
  $(filter $(subst *,%,$2),$d))

ifeq ($(strip $(SRCDIRS)),)
  SCAN_DIRS := ./
else
  SCAN_DIRS := $(foreach d,$(SRCDIRS),$(patsubst %/,%,$(d))/)
endif

EXCLUDE_PATTERNS := ./build/% build/% ./bin/% bin/% ./libs/% libs/%

ALL_EXTS := $(addprefix *,$(SRCEXTS) $(HDREXTS))
RAW := $(sort $(foreach d,$(SCAN_DIRS),$(call rwildcard,$d,$(ALL_EXTS))))
RAW := $(sort $(filter-out $(EXCLUDE_PATTERNS),$(patsubst ./%,%,$(RAW))))
SOURCES := $(sort $(filter $(addprefix %,$(SRCEXTS)),$(RAW)))
HEADERS := $(sort $(filter $(addprefix %,$(HDREXTS)),$(RAW)))

override CPPFLAGS += $(addprefix -I,$(sort $(SCAN_DIRS) $(dir $(HEADERS))))
override CPPFLAGS += $(addprefix -I,$(wildcard libs/*/include))
LDFLAGS  += $(addprefix -L,$(wildcard libs/*/lib))

SRC_CXX := $(filter-out %.c,$(SOURCES))
OBJS    := $(addsuffix .o,$(basename $(SOURCES)))

ifdef NODEP
  DEPFLAGS =
else
  DEPFLAGS = -MMD -MP -MF $(@:.o=.d) -MT $@
endif
DEPS := $(OBJS:.o=.d)

# ---- Target type and entry points -----------------------------------------
MAIN_HINT := (int|void)[[:space:]]+main[[:space:]]*\(
MAIN_RE   := ^[[:space:]]*$(MAIN_HINT)

# Preprocess candidates so comments cannot look like entry points; fall back
# to raw grep if preprocessing fails, so a real main() is never missed.
MAIN_CPP = $(if $(filter %.c,$(1)),$(CC),$(CXX))
MAIN_OK = $(shell { $(call MAIN_CPP,$(1)) -E -P $(CPPFLAGS) $(1) 2>/dev/null || cat $(1); } | grep -qE '$(MAIN_RE)' && echo yes)

ifeq ($(strip $(MAIN_SRCS)),)
  ifneq ($(strip $(SOURCES)),)
    MAIN_CAND := $(strip $(shell grep -lE '$(MAIN_HINT)' $(SOURCES) 2>/dev/null))
    MAIN_MAYBE := $(if $(strip $(MAIN_CAND)),$(strip $(shell grep -lE '/\*|//|^[[:space:]]*[[:punct:]]if' $(MAIN_CAND) 2>/dev/null)))
    MAIN_SRCS := $(strip $(foreach f,$(MAIN_CAND),\
      $(if $(filter $(f),$(MAIN_MAYBE)),\
        $(if $(call MAIN_OK,$(f)),$(f)),\
        $(if $(shell grep -qE '$(MAIN_RE)' $(f) 2>/dev/null && echo yes),$(f)))))
  endif
endif

TYPE := $(strip $(TYPE))
ifeq ($(filter $(TYPE),auto exe static shared),)
  $(error TYPE must be one of: auto, exe, static, shared)
endif
ifeq ($(TYPE),auto)
  ifeq ($(strip $(MAIN_SRCS)),)
    TYPE := shared
  else
    TYPE := exe
  endif
endif
ifeq ($(TYPE),exe)
  ifeq ($(strip $(MAIN_SRCS)),)
    $(error TYPE=exe but no main() found; set MAIN_SRCS=... or use TYPE=auto/static/shared)
  endif
endif
ifeq ($(strip $(SOURCES)),)
  $(warning No source files found (check SRCDIRS); nothing to build)
endif

STEMS     := $(basename $(notdir $(MAIN_SRCS)))
COLLISION :=
ifneq ($(words $(STEMS)),$(words $(sort $(STEMS))))
  COLLISION := 1
endif
EXE_NAME_FOR = $(if $(COLLISION),$(subst /,_,$(basename $(patsubst ./%,%,$(1)))),$(basename $(notdir $(1))))

ifeq ($(words $(MAIN_SRCS)),1)
  EXE_NAMES := $(PROGRAM)
else
  EXE_NAMES := $(foreach s,$(MAIN_SRCS),$(call EXE_NAME_FOR,$(s)))
endif
ifeq ($(TYPE),exe)
  ifneq ($(words $(EXE_NAMES)),$(words $(sort $(EXE_NAMES))))
    $(error Executable name collision after path flattening: $(EXE_NAMES). Set MAIN_SRCS=... or rename directories. To clean, run 'make TYPE=static clean' or remove the binaries manually.)
  endif
endif
EXES := $(addsuffix $(EXE_SUFFIX),$(EXE_NAMES))

MAIN_OBJS   := $(addsuffix .o,$(basename $(MAIN_SRCS)))
COMMON_OBJS := $(filter-out $(MAIN_OBJS),$(OBJS))

ifeq ($(TYPE),static)
  LIB := lib$(PROGRAM).a
else ifeq ($(TYPE),shared)
  LIB := $(SHARED_PREFIX)$(PROGRAM)$(SHARED_SUFFIX)
else
  LIB :=
endif

SHARED_CFLAGS  :=
SHARED_LDFLAGS :=
IMPLIB         :=
ifeq ($(TYPE),shared)
  ifneq ($(PLATFORM),Windows)
    SHARED_CFLAGS := -fPIC
  else
    SHARED_LDFLAGS := -Wl,--export-all-symbols -Wl,--out-implib,lib$(PROGRAM).dll.a
    IMPLIB := lib$(PROGRAM).dll.a
  endif
endif

ifeq ($(strip $(OBJS)),)
  TARGETS :=
else ifeq ($(TYPE),exe)
  TARGETS := $(EXES)
else ifeq ($(strip $(COMMON_OBJS)),)
  $(warning TYPE=$(TYPE) but all objects are entry points; nothing to archive)
  TARGETS :=
else
  TARGETS := $(LIB)
endif

# ---- Rules ----------------------------------------------------------------
Q := $(if $(strip $(V)),,@)

COMPILE.c   = $(CC)  $(EXTRA_CFLAGS) $(CFLAGS)   $(SHARED_CFLAGS) $(CPPFLAGS) $(DEPFLAGS) -c
COMPILE.cxx = $(CXX) $(EXTRA_CFLAGS) $(CXXFLAGS) $(SHARED_CFLAGS) $(CPPFLAGS) $(DEPFLAGS) -c
LINK.c      = $(CC)  $(EXTRA_CFLAGS) $(CFLAGS)   $(LDFLAGS)
LINK.cxx    = $(CXX) $(EXTRA_CFLAGS) $(CXXFLAGS) $(LDFLAGS)
LINK        = $(if $(strip $(SRC_CXX)),$(LINK.cxx),$(LINK.c))

.PHONY: all objs tags ctags clean distclean help show run
.DEFAULT_GOAL := all
.SUFFIXES:

# Explicit per-source rules avoid mingw32-make matching "%.o: %.C" for *.c.
define COMPILE_RULE
$(addsuffix .o,$(basename $(1))): $(1)
	$$(Q)$$(if $$(filter %.c,$$<),$$(COMPILE.c),$$(COMPILE.cxx)) $$< -o $$@
endef
$(foreach s,$(SOURCES),$(eval $(call COMPILE_RULE,$(s))))

ifeq ($(TYPE),exe)
  ifeq ($(words $(MAIN_SRCS)),1)
    EXE_TARGET = $(PROGRAM)$(EXE_SUFFIX)
  else
    EXE_TARGET = $(call EXE_NAME_FOR,$(1))$(EXE_SUFFIX)
  endif
  define EXE_RULE
$(call EXE_TARGET,$(1)): $(basename $(1)).o $(COMMON_OBJS)
	$$(Q)$$(LINK) $$^ $$(EXTRA_LDFLAGS) $$(EXE_LDFLAGS) -o $$@
	@echo "Built executable $$@"
  endef
  $(foreach s,$(MAIN_SRCS),$(eval $(call EXE_RULE,$(s))))
endif

ifneq ($(strip $(LIB)),)
$(LIB): $(COMMON_OBJS)
ifeq ($(TYPE),static)
	$(Q)$(AR) rcs $@ $^
else
	$(Q)$(LINK) -shared $(SHARED_LDFLAGS) -o $@ $^ $(EXTRA_LDFLAGS)
endif
endif

all: $(TARGETS)
objs: $(OBJS)

tags: $(HEADERS) $(SOURCES)
	$(ETAGS) $(ETAGSFLAGS) $(HEADERS) $(SOURCES)
ctags: $(HEADERS) $(SOURCES)
	$(CTAGS) $(CTAGSFLAGS) $(HEADERS) $(SOURCES)

run: all
ifeq ($(TYPE),exe)
  ifeq ($(words $(EXES)),1)
	$(Q)./$(EXES)
  else
	@echo "Multiple executables: $(EXES)"
	@echo "Run one with: ./<name>"
  endif
else
	@echo "TYPE=$(TYPE): nothing to run."
endif

ALL_PRODUCTS := $(EXES) lib$(PROGRAM).a $(SHARED_PREFIX)$(PROGRAM)$(SHARED_SUFFIX) lib$(PROGRAM).dll.a
clean:
	$(Q)$(RM) $(OBJS) $(ALL_PRODUCTS) $(DEPS)
distclean: clean
	$(Q)$(RM) TAGS tags

help:
	@echo "Generic Makefile for C/C++ Projects (v0.8)"
	@echo "Usage: make [TARGET] [VAR=value]"
	@echo "  all       compile and link/archive (default)"
	@echo "  objs      compile only"
	@echo "  run       run executable (lists choices if multiple)"
	@echo "  tags/ctags create editor tags"
	@echo "  clean     remove objects, products and deps"
	@echo "  distclean clean plus editor tags"
	@echo "  show      print effective variables"
	@echo "  help      this message"
	@echo "Vars: TYPE=auto|exe|static|shared  MAIN_SRCS=...  SRCDIRS=..."
	@echo "      V=1  NODEP=yes  EXE_LDFLAGS=-s  CROSS_COMPILE=..."
	@echo "Note: main() detection is grep-based; set TYPE/MAIN_SRCS if needed."
	@echo "      Windows needs a POSIX shell (Git Bash or MSYS2) on PATH."
	@echo "Issues: https://github.com/Cheedoong/MakefileTemplate/issues"

show:
	@echo 'PLATFORM     :' $(PLATFORM)
	@echo 'SHELL        :' $(SHELL)
	@echo 'CC/CXX/AR    :' $(CC) / $(CXX) / $(AR)
	@echo 'TYPE         :' $(TYPE)
	@echo 'PROGRAM      :' $(PROGRAM)
	@echo 'MAIN_SRCS    :' $(MAIN_SRCS)
	@echo 'EXES         :' $(if $(filter exe,$(TYPE)),$(EXES),)
	@echo 'LIB          :' $(LIB)
	@echo 'SRCDIRS      :' $(SCAN_DIRS)
	@echo 'SOURCES      :' $(SOURCES)
	@echo 'HEADERS      :' $(HEADERS)
	@echo 'OBJS         :' $(OBJS)
	@echo 'DEPS         :' $(DEPS)
	@echo 'CFLAGS       :' $(CFLAGS)
	@echo 'CXXFLAGS     :' $(CXXFLAGS)
	@echo 'CPPFLAGS     :' $(CPPFLAGS)
	@echo 'LDFLAGS      :' $(LDFLAGS)
	@echo 'EXTRA_CFLAGS :' $(EXTRA_CFLAGS)
	@echo 'EXTRA_LDFLAGS:' $(EXTRA_LDFLAGS)

ifndef NODEP
ifneq ($(strip $(DEPS)),)
-include $(DEPS)
endif
endif

## End of the Makefile ##  Suggestions are welcome  ## All rights reserved ##
#############################################################################
