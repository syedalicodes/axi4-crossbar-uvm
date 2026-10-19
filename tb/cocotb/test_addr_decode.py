import random

import cocotb
from cocotb.triggers import Timer


@cocotb.test()
async def test_address_decode(dut):
    test_cases = [
        (0x00000000, 1, 0, 0),
        (0x00000001, 1, 0, 0),
        (0x00000FFE, 1, 0, 0),
        (0x00000FFF, 1, 0, 0),
        (0x00001000, 1, 1, 0),
        (0x00001001, 1, 1, 0),
        (0x00001FFE, 1, 1, 0),
        (0x00001FFF, 1, 1, 0),
        (0x00002000, 0, 0, 1),
        (0x00003000, 0, 0, 1),
        (0x80000000, 0, 0, 1),
        (0xFFFFFFFF, 0, 0, 1),
    ]

    rng = random.Random(20261017)
    for _ in range(100):
        address = rng.getrandbits(len(dut.addr))
        if address < 0x2000:
            continue
        test_cases.append((address, 0, 0, 1))

    for address, expected_valid, expected_slave, expected_error in test_cases:
        dut.addr.value = address
        await Timer(10, unit="ns")

        actual = (
            int(dut.decode_valid.value),
            int(dut.slave_sel.value),
            int(dut.decode_error.value),
        )
        expected = (expected_valid, expected_slave, expected_error)

        assert actual == expected, (
            f"Address 0x{address:08X}: "
            f"expected {expected}, got {actual}"
        )

    dut._log.info(
        "PASS: checked %d address decoder cases", len(test_cases)
    )
