import cocotb
from cocotb.clock import Clock
from cocotb.triggers import (
    RisingEdge, ReadOnly, Timer
)
import random


# reset 
async def reset_fifo(dut):
    dut.rst.value = 0
    dut.w_en.value = 0
    dut.r_en.value = 0
    dut.w_data.value = 0
    await Timer(50, units="ns")
    dut.rst.value = 1
    await RisingEdge(dut.w_clk)
    await RisingEdge(dut.r_clk)
    

# write 
async def writer(dut, test_data):
    for val in test_data:
        while dut.full.value:
            await RisingEdge(dut.w_clk)
        dut.w_data.value = val
        dut.w_en.value = 1
        await RisingEdge(dut.w_clk)
        dut.w_en.value = 0
        await Timer(random.randint(5, 20), units="ns")
        

# read 
async def reader(dut, num_items, expected_data):
    read_data = []
    await Timer(100, units="ns")  # Delay to allow writes to get started

    for _ in range(num_items):
        while dut.empty.value:
            await RisingEdge(dut.r_clk)

        dut.r_en.value = 1
        await RisingEdge(dut.r_clk)
        dut.r_en.value = 0

        await RisingEdge(dut.r_clk)
        await ReadOnly()

        raw_val = dut.r_data.value
        if not raw_val.is_resolvable:
            raise TestFailure(f"r_data is unresolvable (x/z): {raw_val}")

        read_val = raw_val.integer
        read_data.append(read_val)

        await Timer(random.randint(5, 20), units="ns")

    assert read_data == expected_data, f"Mismatch! Expected {expected_data}, got {read_data}"


# main 
@cocotb.test()
async def asynch_fifo_test(dut):

    cocotb.start_soon(Clock(dut.r_clk, 13, units='ns').start())
    cocotb.start_soon(Clock(dut.w_clk, 7, units='ns').start())

    await reset_fifo(dut)

    test_data = [random.randint(0, 255) for _ in range(8)]

    await cocotb.start(writer(dut, test_data))
    await cocotb.start(reader(dut, len(test_data), test_data))

    await Timer(2000, units="ns")
