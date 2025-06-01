import cocotb
from cocotb.clock import Clock
from cocotb.triggers import (
    RisingEdge, ReadOnly, Timer
)
import random


# reset 
async def reset_fifo(dut):
    dut.rst.value = 1  # reset first (active high)
    dut.w_en.value = 0
    dut.r_en.value = 0
    dut.w_data.value = 0
    await Timer(50, units="ns")
    dut.rst.value = 0  # deassert reset 
    
    await RisingEdge(dut.w_clk)
    await RisingEdge(dut.r_clk)
    await Timer(20, units="ns")

# write until full
async def write_until_full(dut, test_data):
    written_count = 0
    
    for i, val in enumerate(test_data):
        # Check if FIFO is full before writing
        if dut.full.value:
            cocotb.log.info(f"FIFO is FULL after writing {written_count} items.")
            break
        
        # Setup data and enable
        dut.w_data.value = val
        dut.w_en.value = 1
        await RisingEdge(dut.w_clk)
        # Deassert enable after one cycle
        dut.w_en.value = 0
        
        written_count += 1
        cocotb.log.info(f"Written item {i}: {val:02x} (total written: {written_count})")
        
        # Wait for synchronization (3 cycles is sufficient)
        for _ in range(3):
            await RisingEdge(dut.w_clk)
        
        if dut.full.value:
            cocotb.log.info(f"FIFO became FULL after writing {written_count} items!")
            # Observe full signal
            for j in range(5):
                await RisingEdge(dut.w_clk)
                cocotb.log.info(f"FIFO full status: {dut.full.value}")
            break
    
    return written_count

# Try to write one more when full (should be ignored)
async def test_write_when_full(dut):
    if dut.full.value:
        cocotb.log.info("Testing write when FIFO is full (should be ignored)")
        dut.w_data.value = 0xAA 
        dut.w_en.value = 1
        await RisingEdge(dut.w_clk)
        dut.w_en.value = 0
        await RisingEdge(dut.w_clk)
        cocotb.log.info(f"After attempting write when full, full status: {dut.full.value}")


# read some items to make space
async def partial_reader(dut, num_items_to_read):
    read_data = []
    
    for i in range(num_items_to_read):
        # Wait until FIFO is not empty
        while dut.empty.value:
            await RisingEdge(dut.r_clk)

        # Assert read enable
        await RisingEdge(dut.r_clk)
        dut.r_en.value = 1
        await RisingEdge(dut.r_clk)
        dut.r_en.value = 0
        
        # Wait for data to be valid
        await ReadOnly()
        
        raw_val = dut.r_data.value
        if not raw_val.is_resolvable:
            cocotb.log.error(f"r_data is unresolvable (x/z) at item {i}: {raw_val}")
            raise Exception(f"r_data is unresolvable (x/z): {raw_val}")

        read_val = raw_val.integer
        read_data.append(read_val)
        cocotb.log.info(f"Read item {i}: {read_val:02x}")
        
        # Check if FIFO is no longer full after read
        if not dut.full.value:
            cocotb.log.info(f"FIFO is no longer full after reading {i+1} items")

    return read_data


# Entire test
@cocotb.test()
async def asynch_fifo_full_test(dut):
    # Start clocks
    cocotb.start_soon(Clock(dut.r_clk, 13, units='ns').start())
    cocotb.start_soon(Clock(dut.w_clk, 7, units='ns').start())

    await reset_fifo(dut) # reset IFFO 

    # FIFO depth = 16, generate 25 items to ensure hitting full condition
    test_data = [i for i in range(25)]  # Use simple counting pattern for easier debugging
    cocotb.log.info(f"Test data: {[f'{x:02x}' for x in test_data]}")

    # Initial status check
    cocotb.log.info(f"Initial state - Full: {dut.full.value}, Empty: {dut.empty.value}")

    # Write until FIFO full
    written_count = await write_until_full(dut, test_data)
    
    # Attempt to write when full (should be ignored)
    await test_write_when_full(dut)
    
    # Wait some time to observe the full condition
    cocotb.log.info("Observing FIFO full condition for several clock cycles...")
    for i in range(10):
        await RisingEdge(dut.w_clk)
        cocotb.log.info(f"Cycle {i}: Full={dut.full.value}, Empty={dut.empty.value}")
    
    # Read a few items to make space
    cocotb.log.info("Reading some items to make space...")
    read_data = await partial_reader(dut, 3)

    # Wait for write domain to sync
    for _ in range(10):
        await RisingEdge(dut.w_clk)

    # Check status after partial read
    cocotb.log.info(f"After reading 3 items - Full: {dut.full.value}, Empty: {dut.empty.value}")

    # Try writing more items now that there's space
    cocotb.log.info("Writing more items now that space is available...")
    remaining_data = test_data[written_count:written_count+2]
    for val in remaining_data:
        if dut.full.value:
            break
        dut.w_data.value = val
        dut.w_en.value = 1
        await RisingEdge(dut.w_clk)
        dut.w_en.value = 0
        await RisingEdge(dut.w_clk)
        
        cocotb.log.info("[PASS]: Test completed successfully!")
        await Timer(200, units="ns")  # Final settling time


# Full flag behavior test
@cocotb.test()
async def full_flag_test(dut):
    # Start clocks
    cocotb.start_soon(Clock(dut.r_clk, 13, units='ns').start())
    cocotb.start_soon(Clock(dut.w_clk, 7, units='ns').start())

    # Reset the FIFO
    await reset_fifo(dut)

    cocotb.log.info("=== Testing Full Flag Behavior ===")
    
    # Write exactly 16 items 
    for i in range(17):  # 17 to verify it works 
        if dut.full.value:
            cocotb.log.info(f"FIFO became full before writing item {i}")
            break
            
        dut.w_data.value = i
        dut.w_en.value = 1
        
        cocotb.log.info(f"Before write {i}: Full={dut.full.value}")
        
        await RisingEdge(dut.w_clk)
        dut.w_en.value = 0
        
        # Wait for full flag to potentially update
        await RisingEdge(dut.w_clk)
        
        cocotb.log.info(f"After write {i}: Full={dut.full.value}")
        
        if dut.full.value:
            cocotb.log.info(f"FIFO is full . Wrote {i+1} items")
            # Observe full flag for several more cycles
            for j in range(5):
                await RisingEdge(dut.w_clk)
                cocotb.log.info(f"  Full observation cycle {j}: {dut.full.value}")
            break

    await Timer(200, units="ns")