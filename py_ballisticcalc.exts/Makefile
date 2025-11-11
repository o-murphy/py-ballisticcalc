# ===== Project configuration =====
PROJECT_NAME = bclibc
SRC_DIR = py_ballisticcalc_exts/src
INC_DIR = py_ballisticcalc_exts/include
BUILD_DIR = build
OBJ_DIR = $(BUILD_DIR)/obj
LIB_DIR = $(BUILD_DIR)/lib

# ===== Detect platform =====
UNAME_S := $(shell uname -s)

ifeq ($(UNAME_S),Linux)
    PLATFORM = linux
else ifeq ($(UNAME_S),Darwin)
    PLATFORM = macos
else
    PLATFORM = windows
endif

# ===== Compiler selection =====
ifeq ($(PLATFORM),macos)
    CC = clang
    CXX = clang++
else
    CC ?= gcc
    CXX ?= g++
endif

# ===== Compiler and linker flags =====
CFLAGS_COMMON = -O2 -Wall -g -I$(INC_DIR)
CXXFLAGS_COMMON = -O2 -Wall -g -I$(INC_DIR)
LDFLAGS_COMMON = -shared
ARFLAGS = rcs

ifeq ($(PLATFORM),linux)
    CFLAGS = $(CFLAGS_COMMON) -std=c99 -fPIC
    CXXFLAGS = $(CXXFLAGS_COMMON) -std=c++11 -fPIC
    ifeq ($(DISABLE_SHARED_STRIP),1)
        LDFLAGS = $(LDFLAGS_COMMON)
    else
        LDFLAGS = $(LDFLAGS_COMMON) -Wl,-strip-all
    endif
endif

ifeq ($(PLATFORM),macos)
    CFLAGS = $(CFLAGS_COMMON) -std=c99 -fPIC
    CXXFLAGS = $(CXXFLAGS_COMMON) -std=c++14 -fPIC
    LDFLAGS = $(LDFLAGS_COMMON) -stdlib=libc++
endif

ifeq ($(PLATFORM),windows)
    CFLAGS = $(CFLAGS_COMMON)
    CXXFLAGS = $(CXXFLAGS_COMMON)
    LDFLAGS = $(LDFLAGS_COMMON)
endif

# ===== Sources =====
C_SOURCES := $(wildcard $(SRC_DIR)/*.c)
CPP_SOURCES := $(wildcard $(SRC_DIR)/*.cpp)
OBJS := $(patsubst $(SRC_DIR)/%.c, $(OBJ_DIR)/%.o, $(C_SOURCES)) \
        $(patsubst $(SRC_DIR)/%.cpp, $(OBJ_DIR)/%.o, $(CPP_SOURCES))

# ===== Targets =====
STATIC_LIB = $(LIB_DIR)/lib$(PROJECT_NAME).a
SHARED_LIB = $(LIB_DIR)/lib$(PROJECT_NAME).so

# ===== Default target =====
all: $(STATIC_LIB) $(SHARED_LIB)

# ===== Compilation rules =====
$(OBJ_DIR)/%.o: $(SRC_DIR)/%.c | $(OBJ_DIR)
	@echo "Compiling C: $<"
	$(CC) $(CFLAGS) -c $< -o $@

$(OBJ_DIR)/%.o: $(SRC_DIR)/%.cpp | $(OBJ_DIR)
	@echo "Compiling C++: $<"
	$(CXX) $(CXXFLAGS) -c $< -o $@

# ===== Linking rules =====
$(STATIC_LIB): $(OBJS) | $(LIB_DIR)
	@echo "Creating static library: $@"
	ar $(ARFLAGS) $@ $(OBJS)

$(SHARED_LIB): $(OBJS) | $(LIB_DIR)
	@echo "Creating shared library: $@"
	$(CXX) $(LDFLAGS) -o $@ $(OBJS)

# ===== Directory rules =====
$(OBJ_DIR) $(LIB_DIR):
	mkdir -p $@

# ===== Cleaning =====
clean:
	rm -rf $(BUILD_DIR)

rebuild: clean all

# ===== Info =====
info:
	@echo "Platform: $(PLATFORM)"
	@echo "CC: $(CC)"
	@echo "CXX: $(CXX)"
	@echo "CFLAGS: $(CFLAGS)"
	@echo "CXXFLAGS: $(CXXFLAGS)"
	@echo "LDFLAGS: $(LDFLAGS)"
	@echo "Sources: $(C_SOURCES) $(CPP_SOURCES)"
	@echo "Objects: $(OBJS)"
