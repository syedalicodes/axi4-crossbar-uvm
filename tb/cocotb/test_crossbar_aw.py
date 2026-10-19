import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer


async def settle():
    await Timer(1, unit="ns")


def set_aw(dut, master, valid, addr=0, ident=1):
    getattr(dut, f"{master}_awid").value = ident
    getattr(dut, f"{master}_awaddr").value = addr
    getattr(dut, f"{master}_awlen").value = 0
    getattr(dut, f"{master}_awsize").value = 2
    getattr(dut, f"{master}_awburst").value = 1
    getattr(dut, f"{master}_awvalid").value = valid


def set_w(dut, master, valid, data=0, strb=0xF, last=1):
    getattr(dut, f"{master}_wdata").value = data
    getattr(dut, f"{master}_wstrb").value = strb
    getattr(dut, f"{master}_wlast").value = last
    getattr(dut, f"{master}_wvalid").value = valid


async def accept_aw(dut, master, addr, ident, slave):
    set_aw(dut, master, True, addr, ident)
    await settle()

    assert int(getattr(dut, f"{slave}_awvalid").value) == 1
    assert int(getattr(dut, f"{slave}_awaddr").value) == addr
    assert int(getattr(dut, f"{slave}_awid").value) == ident
    assert int(getattr(dut, f"{master}_awready").value) == 1

    await RisingEdge(dut.aclk)
    await settle()
    set_aw(dut, master, False)


async def send_final_w(dut, master, slave, data, strb=0xF):
    set_w(dut, master, True, data, strb, 1)
    await settle()

    assert int(getattr(dut, f"{slave}_wvalid").value) == 1
    assert int(getattr(dut, f"{slave}_wdata").value) == data
    assert int(getattr(dut, f"{slave}_wstrb").value) == strb
    assert int(getattr(dut, f"{slave}_wlast").value) == 1
    assert int(getattr(dut, f"{master}_wready").value) == 1

    await RisingEdge(dut.aclk)
    await settle()
    set_w(dut, master, False)


@cocotb.test()
async def test_aw_w_routing_and_backpressure(dut):
    """Test AW destination retention, W routing, stalls and contention."""

    cocotb.start_soon(Clock(dut.aclk, 10, unit="ns").start())

    # Initialize all inputs.
    dut.aresetn.value = 0

    for master in ("m0", "m1"):
        set_aw(dut, master, False)
        set_w(dut, master, False)

    dut.s0_awready.value = 1
    dut.s1_awready.value = 1
    dut.s0_wready.value = 1
    dut.s1_wready.value = 1

    await Timer(20, unit="ns")
    dut.aresetn.value = 1
    await settle()

    # Case 1: Master 0 -> Slave 0, including final W beat.
    await accept_aw(dut, "m0", 0x40, 5, "s0")
    await send_final_w(dut, "m0", "s0", 0x12345678, 0xF)

    # Case 2: Master 1 -> Slave 1.
    await accept_aw(dut, "m1", 0x1080, 10, "s1")
    await send_final_w(dut, "m1", "s1", 0xA5A55A5A, 0x5)

    # Case 3: W backpressure. Data must remain visible while stalled.
    await accept_aw(dut, "m1", 0x1100, 12, "s1")
    dut.s1_wready.value = 0
    set_w(dut, "m1", True, 0xDEADBEEF, 0xA, 1)
    await settle()

    assert int(dut.s1_wvalid.value) == 1
    assert int(dut.s1_wdata.value) == 0xDEADBEEF
    assert int(dut.s1_wstrb.value) == 0xA
    assert int(dut.m1_wready.value) == 0

    # One stalled clock edge must not release the destination.
    await RisingEdge(dut.aclk)
    await settle()
    assert int(dut.s1_wvalid.value) == 1
    assert int(dut.s1_wdata.value) == 0xDEADBEEF

    dut.s1_wready.value = 1
    await settle()
    assert int(dut.m1_wready.value) == 1
    await RisingEdge(dut.aclk)
    await settle()
    set_w(dut, "m1", False)

    # Case 4: Same-slave AW contention; master 0 has priority.
    set_aw(dut, "m0", True, 0x80, 1)
    set_aw(dut, "m1", True, 0xC0, 2)
    await settle()

    assert int(dut.s0_awvalid.value) == 1
    assert int(dut.s0_awaddr.value) == 0x80
    assert int(dut.m0_awready.value) == 1
    assert int(dut.m1_awready.value) == 0

    await RisingEdge(dut.aclk)
    await settle()
    set_aw(dut, "m0", False)
    set_aw(dut, "m1", False)
    await send_final_w(dut, "m0", "s0", 0xCAFEBABE)

    # Case 5: Both masters target different slaves concurrently.
    set_aw(dut, "m0", True, 0x100, 3)
    set_aw(dut, "m1", True, 0x1180, 4)
    await settle()

    assert int(dut.s0_awvalid.value) == 1
    assert int(dut.s1_awvalid.value) == 1
    assert int(dut.m0_awready.value) == 1
    assert int(dut.m1_awready.value) == 1

    await RisingEdge(dut.aclk)
    await settle()
    set_aw(dut, "m0", False)
    set_aw(dut, "m1", False)

    # Both W paths can make progress in parallel.
    set_w(dut, "m0", True, 0x11112222, 0xF, 1)
    set_w(dut, "m1", True, 0x33334444, 0x3, 1)
    await settle()

    assert int(dut.s0_wvalid.value) == 1
    assert int(dut.s0_wdata.value) == 0x11112222
    assert int(dut.s1_wvalid.value) == 1
    assert int(dut.s1_wdata.value) == 0x33334444
    assert int(dut.m0_wready.value) == 1
    assert int(dut.m1_wready.value) == 1

    await RisingEdge(dut.aclk)
    await settle()
    set_w(dut, "m0", False)
    set_w(dut, "m1", False)

    # Case 6: Unmapped address must not be accepted.
    set_aw(dut, "m0", True, 0x2000, 7)
    await settle()
    assert int(dut.s0_awvalid.value) == 0
    assert int(dut.s1_awvalid.value) == 0
    assert int(dut.m0_awready.value) == 0
    set_aw(dut, "m0", False)

    dut._log.info("PASS: AW/W routing, destination retention, backpressure, contention, parallel traffic and unmapped address")


@cocotb.test()
async def test_three_beat_burst_with_midburst_stall(dut):
    """Verify W ownership across three beats and a mid-burst stall."""

    cocotb.start_soon(Clock(dut.aclk, 10, unit="ns").start())

    dut.aresetn.value = 0
    for master in ("m0", "m1"):
        set_aw(dut, master, False)
        set_w(dut, master, False)

    dut.s0_awready.value = 1
    dut.s1_awready.value = 1
    dut.s0_wready.value = 1
    dut.s1_wready.value = 1

    await Timer(20, unit="ns")
    dut.aresetn.value = 1
    await settle()

    # Three beats: AXI AWLEN = number of beats minus one.
    set_aw(dut, "m0", True, 0x40, 6)
    dut.m0_awlen.value = 2
    await settle()

    assert int(dut.s0_awvalid.value) == 1
    assert int(dut.s0_awlen.value) == 2
    assert int(dut.m0_awready.value) == 1

    await RisingEdge(dut.aclk)
    await settle()
    set_aw(dut, "m0", False)

    # Beat 1: accepted, not final.
    set_w(dut, "m0", True, 0x11110001, 0xF, 0)
    await settle()
    assert int(dut.s0_wvalid.value) == 1
    assert int(dut.s0_wdata.value) == 0x11110001
    assert int(dut.s0_wlast.value) == 0
    assert int(dut.m0_wready.value) == 1
    await RisingEdge(dut.aclk)
    await settle()

    # Beat 2: apply backpressure and verify stable payload.
    dut.s0_wready.value = 0
    set_w(dut, "m0", True, 0x22220002, 0x5, 0)
    await settle()
    assert int(dut.s0_wvalid.value) == 1
    assert int(dut.s0_wdata.value) == 0x22220002
    assert int(dut.s0_wstrb.value) == 0x5
    assert int(dut.s0_wlast.value) == 0
    assert int(dut.m0_wready.value) == 0

    await RisingEdge(dut.aclk)
    await settle()
    assert int(dut.s0_wvalid.value) == 1
    assert int(dut.s0_wdata.value) == 0x22220002
    assert int(dut.s0_wstrb.value) == 0x5
    assert int(dut.m0_wready.value) == 0

    # Release backpressure and accept beat 2.
    dut.s0_wready.value = 1
    await settle()
    assert int(dut.m0_wready.value) == 1
    await RisingEdge(dut.aclk)
    await settle()

    # Beat 3: final beat; ownership releases on this handshake.
    set_w(dut, "m0", True, 0x33330003, 0xF, 1)
    await settle()
    assert int(dut.s0_wvalid.value) == 1
    assert int(dut.s0_wdata.value) == 0x33330003
    assert int(dut.s0_wlast.value) == 1
    assert int(dut.m0_wready.value) == 1
    await RisingEdge(dut.aclk)
    await settle()
    set_w(dut, "m0", False)

    # Check that S1 can accept a new AW after the burst finishes.
    set_aw(dut, "m1", True, 0x1080, 9)
    await settle()
    assert int(dut.s1_awvalid.value) == 1
    assert int(dut.m1_awready.value) == 1

    dut._log.info(
        "PASS: three-beat W burst, mid-burst backpressure and final-beat release"
    )


@cocotb.test()
async def test_single_beat_burst_releases_ownership(dut):
    """Verify AWLEN=0 completes after one accepted W beat."""

    cocotb.start_soon(Clock(dut.aclk, 10, unit="ns").start())

    dut.aresetn.value = 0
    for master in ("m0", "m1"):
        set_aw(dut, master, False)
        set_w(dut, master, False)

    dut.s0_awready.value = 1
    dut.s1_awready.value = 1
    dut.s0_wready.value = 1
    dut.s1_wready.value = 1

    await Timer(20, unit="ns")
    dut.aresetn.value = 1
    await settle()

    # AWLEN=0 means exactly one expected data beat.
    set_aw(dut, "m0", True, 0x40, 11)
    dut.m0_awlen.value = 0
    await settle()

    assert int(dut.s0_awvalid.value) == 1
    assert int(dut.s0_awlen.value) == 0
    assert int(dut.m0_awready.value) == 1

    await RisingEdge(dut.aclk)
    await settle()
    set_aw(dut, "m0", False)

    # The first accepted W beat should release ownership.
    set_w(dut, "m0", True, 0xABCDEF01, 0xF, 1)
    await settle()

    assert int(dut.s0_wvalid.value) == 1
    assert int(dut.s0_wdata.value) == 0xABCDEF01
    assert int(dut.s0_wlast.value) == 1
    assert int(dut.m0_wready.value) == 1

    await RisingEdge(dut.aclk)
    await settle()
    set_w(dut, "m0", False)

    # Verify the slave can accept a new write after completion.
    set_aw(dut, "m1", True, 0x1080, 12)
    await settle()

    assert int(dut.s1_awvalid.value) == 1
    assert int(dut.m1_awready.value) == 1

    dut._log.info("PASS: single-beat burst and ownership release")


@cocotb.test()
async def test_wlast_mismatch_flags(dut):
    """Verify early and missing WLAST set the diagnostic flags."""

    cocotb.start_soon(Clock(dut.aclk, 10, unit="ns").start())

    dut.aresetn.value = 0
    for master in ("m0", "m1"):
        set_aw(dut, master, False)
        set_w(dut, master, False)

    dut.s0_awready.value = 1
    dut.s1_awready.value = 1
    dut.s0_wready.value = 1
    dut.s1_wready.value = 1

    await Timer(20, unit="ns")
    dut.aresetn.value = 1
    await settle()

    assert int(dut.s0_wlast_error.value) == 0
    assert int(dut.s1_wlast_error.value) == 0

    # S0: AWLEN=2 expects three beats; WLAST=1 on beat 1 is early.
    set_aw(dut, "m0", True, 0x40, 13)
    dut.m0_awlen.value = 2
    await settle()
    assert int(dut.m0_awready.value) == 1
    await RisingEdge(dut.aclk)
    await settle()
    set_aw(dut, "m0", False)

    set_w(dut, "m0", True, 0x1111, 0xF, 1)
    await settle()
    assert int(dut.s0_wvalid.value) == 1
    await RisingEdge(dut.aclk)
    await settle()
    assert int(dut.s0_wlast_error.value) == 1
    set_w(dut, "m0", False)

    # Finish the expected burst so the master can issue another write.
    for data in (0x2222, 0x3333):
        set_w(dut, "m0", True, data, 0xF, 0 if data == 0x2222 else 1)
        await settle()
        assert int(dut.s0_wvalid.value) == 1
        await RisingEdge(dut.aclk)
        await settle()
    set_w(dut, "m0", False)

    # S1: AWLEN=0 expects WLAST=1, but send WLAST=0.
    set_aw(dut, "m1", True, 0x1040, 14)
    dut.m1_awlen.value = 0
    await settle()
    assert int(dut.m1_awready.value) == 1
    await RisingEdge(dut.aclk)
    await settle()
    set_aw(dut, "m1", False)

    set_w(dut, "m1", True, 0x4444, 0xF, 0)
    await settle()
    assert int(dut.s1_wvalid.value) == 1
    await RisingEdge(dut.aclk)
    await settle()
    assert int(dut.s1_wlast_error.value) == 1
    set_w(dut, "m1", False)

    dut._log.info("PASS: early and missing WLAST set their diagnostic flags")
