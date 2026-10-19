# 2×2 AXI Write-Channel Crossbar

[![Language](https://img.shields.io/badge/Language-SystemVerilog-blue)](https://www.systemverilog.org/)
[![Simulation](https://img.shields.io/badge/Simulation-Verilator-green)](https://www.veripool.org/verilator/)
[![Verification](https://img.shields.io/badge/Verification-Cocotb-orange)](https://www.cocotb.org/)
[![Assertions](https://img.shields.io/badge/Assertions-SVA-purple)](https://en.wikipedia.org/wiki/SystemVerilog_Assertions)
[![Status](https://img.shields.io/badge/Status-AW%2FW%20Verification%20Complete-brightgreen)](#verification-results)

A parameterized **2-master × 2-slave AXI-style write-channel crossbar** implemented in SystemVerilog and verified using Cocotb, Verilator, and SystemVerilog Assertions (SVA).

The project focuses on address decoding, write-address arbitration, write-data routing, burst ownership, backpressure handling, randomized testing, and protocol-oriented assertion checks. It is intended as a portfolio project demonstrating RTL design and design-verification practices relevant to digital ASIC and SoC development.

> **Scope:** This implementation covers the write-address (AW) and write-data (W) channels. It is not a complete AXI4 crossbar: write responses (B), read-address (AR), and read-data (R) channels are outside the current scope.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Architecture](#architecture)
- [Address Map](#address-map)
- [Key Design Features](#key-design-features)
- [Design Decisions](#design-decisions)
- [Technology Stack](#technology-stack)
- [Repository Structure](#repository-structure)
- [Verification Strategy](#verification-strategy)
- [Verification Results](#verification-results)
- [Getting Started](#getting-started)
- [Running the Tests](#running-the-tests)
- [Expected Behavior](#expected-behavior)
- [Known Limitations](#known-limitations)
- [Future Enhancements](#future-enhancements)
- [Engineering Skills Demonstrated](#engineering-skills-demonstrated)
- [Author](#author)

## Project Overview

Modern SoC designs use interconnects to connect multiple bus masters to shared memory-mapped peripherals and other slave interfaces. An interconnect must decode addresses, arbitrate for shared destinations, route transactions correctly, and preserve transaction ownership when a receiver applies backpressure.

This project implements a small 2×2 write-channel crossbar to explore these design and verification challenges.

### Project objectives

- Implement address decoding for two slave address regions.
- Arbitrate simultaneous write-address requests.
- Route write-address and write-data channels to the selected slave.
- Track write ownership across multi-beat bursts.
- Support independent traffic to separate slaves when permitted by the design.
- Handle ready/valid backpressure.
- Detect write-last (`WLAST`) mismatches using diagnostic flags.
- Verify normal, boundary, contention, stall, and randomized transaction scenarios.
- Check write-data stability during backpressure using SVA.
- Maintain reproducible, command-line-based regression tests.

## Architecture

The design contains two master interfaces and two slave interfaces.

```text
             +--------------------+
             |      Master 0       |
             |   AW / W Channels  |
             +----------+---------+
                        |
                        |
             +----------v---------+
             |                    |
             |   2 × 2 Write       |---------> Slave 0
             |   Crossbar          |            AW / W
             |                    |
             |                    |---------> Slave 1
             +----------^---------+            AW / W
                        |
                        |
             +----------+---------+
             |      Master 1       |
             |   AW / W Channels  |
             +--------------------+
```

*Conceptual architecture; not a generated RTL schematic.*

### Main functional blocks

| Block | Responsibility |
|---|---|
| Address decoder | Determines the destination slave from the write address. |
| AW arbitration | Selects a requesting master for an available slave. |
| Write ownership tracking | Records the master associated with an active write transaction. |
| W-channel routing | Directs write data and control signals to the selected slave. |
| Burst tracking | Tracks expected write-data beats using `AWLEN`. |
| Diagnostic logic | Sets sticky flags when observed `WLAST` behavior disagrees with the expected burst length. |
| Assertion monitors | Check selected write-data stability requirements under backpressure. |

### Transaction flow

1. A master presents a write-address request.
2. The address decoder determines whether the address maps to Slave 0 or Slave 1.
3. The arbitration logic grants an eligible request when the destination is available.
4. The crossbar records the selected master and transaction state.
5. Write data is routed to the selected slave while preserving ownership.
6. Burst tracking counts accepted write-data beats.
7. The corresponding ownership state is released when the expected number of beats has been accepted.

## Address Map

The current configuration uses two 4 KiB address regions.

| Destination | Base address | Address range | Decode result |
|---|---:|---:|---|
| Slave 0 | `0x0000_0000` | `0x0000_0000–0x0000_0FFF` | Mapped |
| Slave 1 | `0x0000_1000` | `0x0000_1000–0x0000_1FFF` | Mapped |
| Unmapped region | — | Outside both configured ranges | Unmapped |

The address decoder is verified against mapped addresses, region boundaries, and unmapped addresses.

## Key Design Features

### 1. Address decoding

- Supports two configured slave regions.
- Separates destination selection from transaction routing.
- Exercises base addresses, upper boundaries, and unmapped addresses in regression tests.

### 2. Write-address arbitration

- Implements M0 priority when both masters request the same available slave.
- Tracks destination availability before granting a request.
- Allows independent destination traffic when the relevant ownership conditions permit it.

**Arbitration note:** The implemented policy is priority-based, not round-robin. Fairness under continuous contention is not guaranteed.

### 3. Write-data routing and ownership

- Maintains transaction ownership while a burst is active.
- Prevents a different master from taking over an active destination's write-data stream.
- Tracks active write transactions per master.
- Supports testing of simultaneous traffic directed to different slaves.

### 4. Burst tracking

- Uses the accepted write-address transaction's `AWLEN` to determine the expected number of data beats.
- Supports single-beat and multi-beat burst scenarios.
- Releases ownership according to the expected beat count rather than relying solely on `WLAST`.

### 5. Backpressure handling

- Tests write-data stalls caused by a slave deasserting `WREADY`.
- Checks that write-data routing and payload stability are preserved during the monitored stall conditions.
- Includes SVA checks for write-data stability on both slave interfaces.

### 6. Write-last diagnostics

- Includes sticky diagnostic flags for write-last mismatches on each slave.
- Tests mismatches between the observed `WLAST` signal and the expected burst termination.
- Uses separate negative tests to demonstrate that the relevant stability assertions detect injected violations.

## Design Decisions

The following choices define the current implementation and its verification scope.

| Decision | Rationale |
|---|---|
| 2×2 topology | Small enough for focused verification while exposing arbitration and routing interactions. |
| Fixed M0 priority | Keeps arbitration behavior deterministic and easy to verify. |
| Per-destination ownership | Keeps an active write-data stream associated with its selected master. |
| Per-master active-write tracking | Prevents a master from starting another write burst while its existing burst is active under the current design policy. |
| `AWLEN`-based beat counting | Provides an expected burst length for ownership release and `WLAST` diagnostics. |
| Cocotb with Verilator | Enables automated, repeatable command-line RTL regression testing. |
| SVA negative tests | Demonstrate assertion sensitivity by deliberately injecting a monitored protocol violation. |

## Technology Stack

| Technology | Usage |
|---|---|
| SystemVerilog | RTL implementation and assertion-based checks |
| Verilator | RTL compilation, linting, and simulation |
| Cocotb | Python-based automated testbenches |
| Python | Directed and randomized test generation |
| SVA | Write-data stability checks |
| Make | Reproducible build and regression commands |
| Git and GitHub | Version control and project publication |
| Ubuntu on WSL2 | Development environment |

The current repository uses an open-source simulation flow. Vivado and a physical FPGA board are not required to run the documented tests.

## Repository Structure

```text
axi4-crossbar-uvm/
├── rtl/
│   ├── axi4_addr_decode.sv
│   └── axi4_crossbar_2x2.sv
├── tb/
│   ├── cocotb/
│   │   ├── test_addr_decode.py
│   │   ├── test_crossbar_aw.py
│   │   └── test_crossbar_random.py
│   └── sva/
│       ├── axi4_crossbar_sva.sv
│       ├── axi4_crossbar_sva_top.sv
│       ├── tb_sva_negative.sv
│       └── tb_sva_negative_s1.sv
├── .gitignore
├── Makefile
├── Makefile.crossbar
└── README.md
```

### Important files

- `rtl/axi4_addr_decode.sv` — address decoding logic.
- `rtl/axi4_crossbar_2x2.sv` — crossbar write-channel RTL.
- `tb/cocotb/test_addr_decode.py` — address decoder regression.
- `tb/cocotb/test_crossbar_aw.py` — directed crossbar transaction tests.
- `tb/cocotb/test_crossbar_random.py` — randomized sequential write-burst tests.
- `tb/sva/axi4_crossbar_sva.sv` — assertion checks for write-data stability under stalls.
- `tb/sva/tb_sva_negative.sv` — negative assertion test for Slave 0.
- `tb/sva/tb_sva_negative_s1.sv` — negative assertion test for Slave 1.
- `Makefile` — decoder simulation flow.
- `Makefile.crossbar` — crossbar regression flow.

## Verification Strategy

Verification combines directed testing, randomized testing, boundary checks, backpressure scenarios, and assertion-based negative testing.

### Address decoder regression

The decoder tests cover:

- Mapped addresses in Slave 0's region.
- Mapped addresses in Slave 1's region.
- Base and upper-boundary addresses.
- Unmapped addresses outside the configured regions.

### Directed crossbar regression

The directed tests exercise:

- AW/W routing.
- Destination retention during a write transaction.
- Write-data backpressure.
- Contention for a destination.
- Parallel traffic to separate destinations.
- Unmapped-address handling.
- Single-beat burst ownership release.
- Multi-beat burst operation with a mid-burst stall.
- `WLAST` mismatch diagnostics.

### Randomized regression

The randomized test executes 40 sequential write bursts using a fixed seed (`20261019`) for reproducibility.

The purpose is to explore a wider range of transaction values and burst scenarios than a small set of hand-written cases.

### Assertion-based verification

SVA monitors check write-data stability under the monitored stall conditions for both slave interfaces.

The negative tests intentionally violate the monitored stability requirement. An assertion firing in these tests is the expected outcome and demonstrates that the assertion detects the injected violation.

> These tests validate the implemented scope. They do not establish full AXI4 protocol compliance or exhaustive correctness.

## Verification Results

The following results were observed in the current project regression runs.

| Verification item | Recorded result |
|---|---|
| Address decoder | 112 address cases passed |
| Crossbar regression | 5 tests passed |
| Randomized sequential bursts | 40 bursts |
| Slave 0 SVA negative test | Expected assertion triggered |
| Slave 1 SVA negative test | Expected assertion triggered |

### Crossbar test cases

1. `test_aw_w_routing_and_backpressure`
2. `test_three_beat_burst_with_midburst_stall`
3. `test_single_beat_burst_releases_ownership`
4. `test_wlast_mismatch_flags`
5. `test_randomized_sequential_write_bursts`

**Recorded regression summary:** `TESTS=5 PASS=5 FAIL=0 SKIP=0`

The negative assertion tests are separate from the normal passing regression and are expected to trigger their targeted assertions.

These are recorded development results, not a claim of independent certification, formal proof of the complete design, or sign-off against the full AXI4 specification.

## Getting Started

### Prerequisites

Install or prepare:

- Ubuntu 22.04 or a compatible Linux environment.
- Python 3.
- Verilator.
- Cocotb.
- GNU Make.
- Git.

The project was developed in Ubuntu on WSL2 using a Python virtual environment.

### Clone the repository

```bash
git clone https://github.com/syedalicodes/axi4-crossbar-uvm.git
cd axi4-crossbar-uvm
```

### Activate the project environment

If you have already created the project's virtual environment:

```bash
source .venv/bin/activate
```

If required dependencies are not installed, create an environment and install Cocotb:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install cocotb==2.1.0
```

Confirm that the tools are available:

```bash
verilator --version
python --version
cocotb-config --version
make --version
```

## Running the Tests

### 1. Run the address decoder regression

```bash
source .venv/bin/activate
make SIM=verilator
```

The testbench exercises the configured address regions and unmapped addresses.

### 2. Run the crossbar regression

```bash
source .venv/bin/activate
make -f Makefile.crossbar SIM=verilator
```

The regression runs the directed and randomized Cocotb crossbar tests.

### 3. Run the negative SVA tests

The SVA negative-test tops are separate test configurations. Use the Verilator compile and simulation commands defined or required by the testbench setup for each top:

- `tb/sva/tb_sva_negative.sv`
- `tb/sva/tb_sva_negative_s1.sv`

These tests are intended to trigger their corresponding assertions. A nonzero simulation exit caused by the expected assertion is not the same as a failure of the normal regression.

## Expected Behavior

For the implemented address and write-channel scope, the design is intended to:

- Route mapped write requests to their configured destination.
- Apply the documented fixed-priority arbitration policy.
- Preserve write ownership while a burst is active.
- Route write data according to the selected transaction.
- Handle tested backpressure scenarios.
- Track expected burst length from `AWLEN`.
- Set diagnostic flags for the tested `WLAST` mismatch scenarios.
- Detect injected write-data instability through the targeted SVA checks.

These behaviors should be interpreted within the limitations described below.

## Known Limitations

This is a deliberately scoped write-channel project, not a production-ready or fully AXI4-compliant interconnect.

Current limitations include:

- Only the AW and W channels are implemented in the project scope.
- The B response channel is not implemented.
- The AR and R read channels are not implemented.
- The design does not claim complete AXI4 protocol compliance.
- Arbitration uses fixed M0 priority and does not guarantee fairness.
- The current verification is Cocotb-based; a complete UVM environment is not included.
- Functional coverage closure and full protocol-compliance coverage are not claimed.
- Formal verification of the complete design has not been claimed.
- Timing closure, physical implementation, PPA characterization, and silicon validation are outside the current scope.

## Future Enhancements

Potential next steps for extending the project toward a more comprehensive SoC interconnect verification environment:

1. **Complete AXI4 write path** — implement and verify B-channel responses and error handling.
2. **Read-channel support** — add AR arbitration, read routing, and R-channel response handling.
3. **UVM environment** — develop agents, drivers, monitors, sequencers, scoreboards, and reusable tests.
4. **Functional coverage** — add covergroups and coverage targets for address regions, contention, stalls, burst lengths, and corner cases.
5. **Protocol assertions** — expand SVA checks for the supported AXI channels and relevant handshake rules.
6. **Constrained-random testing** — introduce more diverse traffic, interleavings, and reproducible seeds.
7. **Reference-model scoreboard** — compare observed transactions against an independently defined expected model.
8. **Regression automation** — add scripts and CI checks to make tests reproducible on each change.
9. **Formal checks** — investigate bounded or property-based formal verification for selected control properties.
10. **Performance evaluation** — measure throughput and latency under defined traffic patterns once the relevant response behavior is implemented.

These are proposed extensions, not features claimed to be complete in the current repository.

## Engineering Skills Demonstrated

This project demonstrates hands-on work with:

- RTL design using SystemVerilog.
- Address decoding and arbitration.
- Ready/valid handshake reasoning.
- Burst tracking and transaction ownership.
- Cocotb-based directed and randomized verification.
- Verilator-based simulation.
- Assertion-based verification and negative testing.
- Regression organization and reproducible testing.
- Git-based version control and technical documentation.

## Author

**Syed Ali U Khan**

Electronics and Communication Engineering | Microelectronic System Design

GitHub: [@syedalicodes](https://github.com/syedalicodes)

---

*This repository is an educational and portfolio project demonstrating selected RTL design and verification techniques. It is not represented as a certified, production-ready AXI4 interconnect.*
