.ONESHELL:
SHELL = /bin/bash
.SHELLFLAGS += -e

RM := rm -rf
CP := cp -rf
MKDIR := mkdir
MV := mv
LIBDASHAPI := dashapi
DASH_API_DIR := ../..
DASH_API_PROTO_DIR := $(DASH_API_DIR)/proto
BUILD_DIR := $(DASH_API_DIR)/build
MISC_DIR := $(DASH_API_DIR)/misc
TEST_DIR := $(MISC_DIR)/tests

all: compile_cpp_proto test


compile_cpp_proto:
	$(MKDIR) -p $(BUILD_DIR)
	protoc -I=$(DASH_API_PROTO_DIR) --cpp_out=$(BUILD_DIR) $(DASH_API_PROTO_DIR)/*.proto

dashapi.so: compile_cpp_proto
	g++ -std=c++14 -fPIC -shared -o $(BUILD_DIR)/lib$(LIBDASHAPI).so $(wildcard $(BUILD_DIR)/*.pb.cc) $(wildcard $(MISC_DIR)/*.cpp) -lprotobuf

test: dashapi.so compile_cpp_proto
	g++ -std=c++14 \
		-D PROTO_PATH=\"$(DASH_API_PROTO_DIR)\" \
		-I $(BUILD_DIR) -I $(MISC_DIR) \
		$(wildcard $(TEST_DIR)/*.cpp) \
		-L$(BUILD_DIR) -l$(LIBDASHAPI) -lprotobuf -lgtest -lpthread -lboost_system -lboost_filesystem \
		-o $(TEST_DIR)/test
	LD_LIBRARY_PATH=$(BUILD_DIR) $(TEST_DIR)/test
