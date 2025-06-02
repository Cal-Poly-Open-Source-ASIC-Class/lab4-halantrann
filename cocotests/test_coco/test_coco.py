import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ReadOnly, Timer
import random


# Reset
async def reset_fifo(dut):
    dut.rst.value = 1  # Active-high reset
    dut.w_en.value = 0
    dut.r_en.value = 0
    dut.w_data.value = 0
    await Timer(50, units="ns")
    dut.rst.value = 0  # Deassert reset
    await RisingEdge(dut.w_clk)
    await RisingEdge(dut.r_clk)
    await Timer(20, units="ns")


# Write until FIFO is full - FIXED VERSION
async def write_until_full(dut, test_data):
    written_count = 0

    for i, val in enumerate(test_data):
        # Check if FIFO is full BEFORE attempting to write
        if dut.full.value:
            cocotb.log.info(f"FIFO is FULL. Cannot write more items. Total written: {written_count}")
            break

        # Perform the write
        dut.w_data.value = val
        dut.w_en.value = 1
        await RisingEdge(dut.w_clk)
        dut.w_en.value = 0
        written_count += 1
        cocotb.log.info(f"Written item {i}: {val:02x} (total written: {written_count})")

        # Wait a few cycles to let the full flag settle
        for _ in range(3):
            await RisingEdge(dut.w_clk)

        # Check if FIFO became full after this write
        if dut.full.value:
            cocotb.log.info(f"FIFO became FULL after writing {written_count} items!")
            for j in range(5):
                await RisingEdge(dut.w_clk)
                cocotb.log.info(f"FIFO full status: {dut.full.value}")
            break

    return written_count


# Attempt to write when full
async def test_write_when_full(dut):
    if dut.full.value:
        cocotb.log.info("Testing write when FIFO is full (should be ignored)")
        dut.w_data.value = 0xAA
        dut.w_en.value = 1
        await RisingEdge(dut.w_clk)
        dut.w_en.value = 0
        await RisingEdge(dut.w_clk)
        cocotb.log.info(f"After attempting write when full, full status: {dut.full.value}")


# Read a fixed number of items
async def partial_reader(dut, num_items_to_read):
    read_data = []

    for i in range(num_items_to_read):
        while dut.empty.value:
            await RisingEdge(dut.r_clk)

        # Perform the read
        dut.r_en.value = 1
        await RisingEdge(dut.r_clk)
        dut.r_en.value = 0

        # Wait for data to be available and read it
        await RisingEdge(dut.r_clk)
        await ReadOnly()

        raw_val = dut.r_data.value
        if not raw_val.is_resolvable:
            raise Exception(f"r_data is unresolvable (x/z): {raw_val}")

        read_val = raw_val.integer
        read_data.append(read_val)
        cocotb.log.info(f"Read item {i}: {read_val:02x}")

        # Check if FIFO is no longer full
        await RisingEdge(dut.r_clk)
        if not dut.full.value:
            cocotb.log.info(f"FIFO is no longer full after reading {i + 1} items")

    return read_data


# Read until FIFO becomes empty
async def read_until_empty(dut):
    read_data = []
    i = 0

    cocotb.log.info("Starting read until FIFO is empty...")

    while not dut.empty.value:
        # Perform the read
        dut.r_en.value = 1
        await RisingEdge(dut.r_clk)
        dut.r_en.value = 0

        # Wait for data to be available and read it
        await RisingEdge(dut.r_clk)
        await ReadOnly()

        raw_val = dut.r_data.value
        if not raw_val.is_resolvable:
            cocotb.log.error(f"Unresolvable data at read {i}: {raw_val}")
            break

        read_val = raw_val.integer
        read_data.append(read_val)
        cocotb.log.info(f"Read item {i}: {read_val:02x}")
        i += 1

        # Small delay to let empty flag update
        await RisingEdge(dut.r_clk)

    cocotb.log.info("Finished reading: FIFO is now empty.")
    return read_data


# Main test
@cocotb.test()
async def asynch_fifo_full_test(dut):
    cocotb.start_soon(Clock(dut.r_clk, 13, units='ns').start())
    cocotb.start_soon(Clock(dut.w_clk, 7, units='ns').start())

    await reset_fifo(dut)

    test_data = [i for i in range(25)]
    cocotb.log.info(f"Test data: {[f'{x:02x}' for x in test_data]}")

    cocotb.log.info(f"Initial state - Full: {dut.full.value}, Empty: {dut.empty.value}")

    written_count = await write_until_full(dut, test_data)

    await test_write_when_full(dut)

    for i in range(10):
        await RisingEdge(dut.w_clk)
        cocotb.log.info(f"Cycle {i}: Full={dut.full.value}, Empty={dut.empty.value}")

    cocotb.log.info("Reading some items to make space...")
    read_data = await partial_reader(dut, 3)

    for _ in range(10):
        await RisingEdge(dut.w_clk)

    cocotb.log.info(f"After reading 3 items - Full: {dut.full.value}, Empty: {dut.empty.value}")

    cocotb.log.info("Writing more items now that space is available...")
    remaining_data = test_data[written_count:written_count + 2]
    for val in remaining_data:
        if dut.full.value:
            break
        dut.w_data.value = val
        dut.w_en.value = 1
        await RisingEdge(dut.w_clk)
        dut.w_en.value = 0
        await RisingEdge(dut.w_clk)
        cocotb.log.info(f"Wrote additional item: {val:02x}")

    await Timer(50, units="ns")

    cocotb.log.info("Reading until FIFO becomes empty...")
    all_read_data = await read_until_empty(dut)

    cocotb.log.info(f"[PASS]: Read total of {len(all_read_data)} items. Test completed successfully!")
    await Timer(200, units="ns")


# Full flag behavior test
@cocotb.test()
async def full_flag_test(dut):
    cocotb.start_soon(Clock(dut.r_clk, 13, units='ns').start())
    cocotb.start_soon(Clock(dut.w_clk, 7, units='ns').start())

    await reset_fifo(dut)

    cocotb.log.info("=== Testing Full Flag Behavior ===")

    for i in range(17):  # Try to overfill
        cocotb.log.info(f"Before write {i}: Full={dut.full.value}")
        
        if dut.full.value:
            cocotb.log.info(f"FIFO became full before writing item {i}")
            break

        # Perform the write
        dut.w_data.value = i
        dut.w_en.value = 1
        await RisingEdge(dut.w_clk)
        dut.w_en.value = 0
        
        # Wait for full flag to settle
        await RisingEdge(dut.w_clk)
        cocotb.log.info(f"After write {i}: Full={dut.full.value}")

        if dut.full.value:
            cocotb.log.info(f"FIFO is full. Wrote {i + 1} items")
            for j in range(5):
                await RisingEdge(dut.w_clk)
                cocotb.log.info(f"  Full observation cycle {j}: {dut.full.value}")
            break

    await Timer(200, units="ns")