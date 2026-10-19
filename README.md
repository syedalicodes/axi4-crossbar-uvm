# 2x2 AXI Write-Channel Crossbar

SystemVerilog RTL design and verification project using Verilator, Cocotb, and SystemVerilog Assertions (SVA).

## Scope

Implements AW and W write-channel routing for two masters and two slaves. This is a partial AXI implementation; B responses and read channels are not implemented.

## Verification Results

- Address decoder: 112 cases passed.
- Crossbar regression: 5 tests passed, 0 failed.
- Randomized regression: 40 sequential write bursts passed.
- S0 and S1 negative SVA tests detected intentionally injected violations.

## Run Tests

```bash
source .venv/bin/activate
make SIM=verilator
make -f Makefile.crossbar SIM=verilator
```
