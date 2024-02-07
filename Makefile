.ONESHELL:
SHELL = /bin/bash
.SHELLFLAGS += -e

RM := rm -rf
CP := cp -rf
MKDIR := mkdir
MV := mv
PKGNAME := dash_api
LIBNAME := dashapi
LIBDASHAPI := lib$(LIBNAME).so
BUILD_DIR := build
DESTDIR := 
DASH_API_PROTO_DIR := proto
MISC_DIR := misc
PYPKG_DIR := $(MISC_DIR)/pypkg/$(PKGNAME)
TEST_DIR := $(MISC_DIR)/tests
INSTALLED_HEADER_DIR := $(DESTDIR)/usr/include/$(PKGNAME)
INSTALLED_BIN := $(DESTDIR)/usr/bin
INSTALLED_LIB_DIR := $(DESTDIR)/usr/lib
INSTALLED_PYTHON_DIR := $(DESTDIR)/usr/lib/python3/dist-packages/$(PKGNAME)
PYINCLUDE := $(shell python3 -c "import sys; import sysconfig; sys.stdout.write(sysconfig.get_config_var('INCLUDEPY'))")
PYLIBRARY := $(shell python3 -c "import sys; import sysconfig; sys.stdout.write(sysconfig.get_config_var('BLDLIBRARY'))")

all: compile_cpp_proto dashapi.so compile_py_proto swig

compile_cpp_proto:
	$(MKDIR) -p $(BUILD_DIR)
	protoc -I=$(DASH_API_PROTO_DIR) --cpp_out=$(BUILD_DIR) $(DASH_API_PROTO_DIR)/*.proto

dashapi.so: compile_cpp_proto
	g++ -std=c++14 -fPIC -shared -o $(BUILD_DIR)/$(LIBDASHAPI) $(wildcard $(BUILD_DIR)/*.pb.cc) $(wildcard $(MISC_DIR)/*.cpp) -lprotobuf

compile_py_proto:
	protoc -I=$(DASH_API_PROTO_DIR) --python_out=$(PYPKG_DIR) $(DASH_API_PROTO_DIR)/*.proto
	protoc -I=$(DASH_API_PROTO_DIR) --pyi_out=$(PYPKG_DIR) $(DASH_API_PROTO_DIR)/*.proto

swig:
	swig -c++ -python -py3 -outdir $(PYPKG_DIR) -o $(BUILD_DIR)/utils_wrap.cpp $(MISC_DIR)/utils.i
	g++ -std=c++14 -shared -I$(PYINCLUDE) -fPIC -I$(MISC_DIR) -o $(PYPKG_DIR)/_utils.so $(MISC_DIR)/utils.cpp $(BUILD_DIR)/utils_wrap.cpp $(wildcard $(BUILD_DIR)/*.pb.cc) $(PYLIBRARY) -lprotobuf

clean:
	$(RM) $(BUILD_DIR)
	$(RM) $(PYPKG_DIR)/*_pb2.py

install:
	$(MKDIR) -p $(INSTALLED_HEADER_DIR)
	$(CP) $(BUILD_DIR)/*.pb.h $(INSTALLED_HEADER_DIR)
	$(CP) $(MISC_DIR)/*.h $(INSTALLED_HEADER_DIR)

	$(MKDIR) -p $(INSTALLED_LIB_DIR)
	$(CP) $(BUILD_DIR)/$(LIBDASHAPI) $(INSTALLED_LIB_DIR)

	$(MKDIR) -p $(INSTALLED_PYTHON_DIR)
	$(CP) $(PYPKG_DIR)/*.py $(INSTALLED_PYTHON_DIR)
	$(CP) $(PYPKG_DIR)/*.pyi $(INSTALLED_PYTHON_DIR)

	$(CP) $(PYPKG_DIR)/_utils.so $(INSTALLED_PYTHON_DIR)

	$(MKDIR) -p $(INSTALLED_BIN)
	$(CP) $(MISC_DIR)/dash_api_utils $(INSTALLED_BIN)
	chmod +x $(INSTALLED_BIN)/dash_api_utils

uninstall:
	$(RM) $(INSTALLED_HEADER_DIR)
	$(RM) $(INSTALLED_LIB_DIR)/$(LIBDASHAPI)
	$(RM) $(INSTALLED_PYTHON_DIR)

test: dashapi.so compile_cpp_proto
	g++ -std=c++14 \
		-D PROTO_PATH=\"$(DASH_API_PROTO_DIR)\" \
		-I $(BUILD_DIR) -I $(MISC_DIR) \
		$(wildcard $(TEST_DIR)/*.cpp) \
		-L$(BUILD_DIR) -l$(LIBNAME) -lprotobuf -lgtest -lpthread -lboost_system -lboost_filesystem \
		-o $(TEST_DIR)/test
	LD_LIBRARY_PATH=$(BUILD_DIR) $(TEST_DIR)/test
	python3 -m pytest

.PHONY: uninstall clean
