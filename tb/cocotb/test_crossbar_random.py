import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer


SEED = 20261019


async def settle():
    await Timer(1, unit="ns")


def set_aw(dut, master, valid, addr=0, ident=1, length=0):
    getattr(dut, f"{master}_awid").value = ident
    getattr(dut, f"{master}_awaddr").value = addr
    getattr(dut, f"{master}_awlen").value = length
    getattr(dut, f"{master}_awsize").value = 2
    getattr(dut, f"{master}_awburst").value = 1
    getattr(dut, f"{master}_awvalid").value = valid


def set_w(dut, master, valid, data=0, strb=0xF, last=0):
    getattr(dut, f"{master}_wdata").value = data
    getattr(dut, f"{master}_wstrb").value = strb
    getattr(dut, f"{master}_wlast").value = last
    getattr(dut, f"{master}_wvalid").value = valid


@cocotb.test()
async def test_randomized_sequential_write_bursts(dut):
    """Repeatable randomized bursts, routing, and W-channel backpressure."""
    rng = random.Random(SEED)

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

    transactions = 40

    for txn in range(transactions):
        master = rng.choice(("m0", "m1"))
        slave = rng.choice(("s0", "s1"))
        base = 0x0000 if slave == "s0" else 0x1000
        addr = base + rng.randrange(0, 0x1000, 4)
        awlen = rng.randint(0, 7)
        ident = txn & 0xF

        set_aw(dut, master, True, addr, ident, awlen)
        await settle()

        assert int(getattr(dut, f"{slave}_awvalid").value) == 1, (
            f"txn {txn}: AW not routed to {slave}, addr=0x{addr:08X}"
        )
        assert int(getattr(dut, f"{slave}_awaddr").value) == addr
        assert int(getattr(dut, f"{slave}_awlen").value) == awlen
        assert int(getattr(dut, f"{master}_awready").value) == 1

        await RisingEdge(dut.aclk)
        await settle()
        set_aw(dut, master, False)

        # AXI AWLEN encodes beats-minus-one.
        for beat in range(awlen + 1):
            data = rng.getrandbits(32)
            strb = rng.randint(0, 0xF)
            last = int(beat == awlen)

            # Occasionally stall the target slave before accepting the beat.
            stall_cycles = rng.randint(0, 3)
            getattr(dut, f"{slave}_wready").value = 0 if stall_cycles else 1
            set_w(dut, master, True, data, strb, last)
            await settle()

            for _ in range(stall_cycles):
                assert int(getattr(dut, f"{slave}_wvalid").value) == 1
                assert int(getattr(dut, f"{slave}_wdata").value) == data
                assert int(getattr(dut, f"{slave}_wstrb").value) == strb
                assert int(getattr(dut, f"{slave}_wlast").value) == last
                assert int(getattr(dut, f"{master}_wready").value) == 0

                await RisingEdge(dut.aclk)
                await settle()

            getattr(dut, f"{slave}_wready").value = 1
            await settle()

            assert int(getattr(dut, f"{slave}_wvalid").value) == 1
            assert int(getattr(dut, f"{slave}_wdata").value) == data
            assert int(getattr(dut, f"{slave}_wstrb").value) == strb
            assert int(getattr(dut, f"{slave}_wlast").value) == last
            assert int(getattr(dut, f"{master}_wready").value) == 1

            await RisingEdge(dut.aclk)
            await settle()

        set_w(dut, master, False)
        getattr(dut, f"{slave}_wready").value = 1
        await settle()

    assert int(dut.s0_wlast_error.value) == 0, "Unexpected S0 WLAST error"
    assert int(dut.s1_wlast_error.value) == 0, "Unexpected S1 WLAST error"

    dut._log.info(
        "PASS: %d randomized sequential bursts, seed=%d",
        transactions,
        SEED,
    )
