SIM ?= verilator

TOPLEVEL_LANG = verilog
VERILOG_SOURCES = $(PWD)/rtl/axi4_addr_decode.sv

TOPLEVEL = axi4_addr_decode
COCOTB_TEST_MODULES = test_addr_decode

include $(shell cocotb-config --makefiles)/Makefile.sim

PYTHONPATH := $(PWD)/tb/cocotb:$(PYTHONPATH)
export PYTHONPATH
