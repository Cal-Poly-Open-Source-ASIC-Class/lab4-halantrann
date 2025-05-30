import cocotb
from cocotb.clock import Clock
from cocotb.triggers import (
    RisingEdge, ReadOnly, Timer
)
import random


# reset 
async def reset_fifo(dut):
    dut.rst.value = 1  # Assert reset first
    dut.w_en.value = 0
    dut.r_en.value = 0
    dut.w_data.value = 0
    await Timer(50, units="ns")
    dut.rst.value = 0  # Deassert reset (active-high reset)
    await RisingEdge(dut.w_clk)
    await RisingEdge(dut.r_clk)
    await Timer(20, units="ns")  # Additional settling time
    

# write 
async def writer(dut, test_data):
    for val in test_data:
        # Wait until FIFO is not full
        while dut.full.value:
            await RisingEdge(dut.w_clk)
        
        # Setup data and enable on the same clock edge
        dut.w_data.value = val
        dut.w_en.value = 1
        await RisingEdge(dut.w_clk)
        dut.w_en.value = 0

        await RisingEdge(dut.w_clk)
       

# read 
async def reader(dut, num_items, expected_data):
    read_data = []
    await Timer(100, units="ns")  # Delay to allow writes to get started

    for i in range(num_items):
        # Wait until FIFO is not empty
        while dut.empty.value:
            await RisingEdge(dut.r_clk)

        # Assert read enable and wait for clock edge
        dut.r_en.value = 1
        await RisingEdge(dut.r_clk)
        
        # Keep r_en high for one more cycle to ensure proper read
        await RisingEdge(dut.r_clk)
        dut.r_en.value = 0
        
        # Wait for ReadOnly phase to ensure stable data
        await ReadOnly()

        raw_val = dut.r_data.value
        if not raw_val.is_resolvable:
            cocotb.log.error(f"r_data is unresolvable (x/z) at item {i}: {raw_val}")
            raise Exception(f"r_data is unresolvable (x/z): {raw_val}")

        read_val = raw_val.integer
        read_data.append(read_val)
        cocotb.log.info(f"Read item {i}: {read_val:02x}")

        # Optional: Add delay between reads
        # await Timer(10, units="ns")

    assert read_data == expected_data, f"Mismatch! Expected {expected_data}, got {read_data}"
    cocotb.log.info("All data read successfully!")


# Alternative reader with better timing control
async def reader_v2(dut, num_items, expected_data):
    read_data = []
    await Timer(100, units="ns")  # Delay to allow writes to get started

    for i in range(num_items):
        # Wait until FIFO is not empty
        while dut.empty.value:
            await RisingEdge(dut.r_clk)

        # Method 2: Hold r_en high for exactly one clock cycle
        await RisingEdge(dut.r_clk)  # Align to clock edge first
        dut.r_en.value = 1
        await RisingEdge(dut.r_clk)  # r_en active for one full cycle
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

    assert read_data == expected_data, f"Mismatch! Expected {expected_data}, got {read_data}"
    cocotb.log.info("All data read successfully!")


# main 
@cocotb.test()
async def asynch_fifo_test(dut):
    # Start clocks
    cocotb.start_soon(Clock(dut.r_clk, 13, units='ns').start())
    cocotb.start_soon(Clock(dut.w_clk, 7, units='ns').start())

    # Reset the FIFO
    await reset_fifo(dut)

    # Generate test data
    test_data = [random.randint(0, 255) for _ in range(8)]
    cocotb.log.info(f"Test data: {[f'{x:02x}' for x in test_data]}")

    # Start writer and reader concurrently
    writer_task = cocotb.start_soon(writer(dut, test_data))
    reader_task = cocotb.start_soon(reader_v2(dut, len(test_data), test_data))

    # Wait for both to complete
    await writer_task
    await reader_task

    cocotb.log.info("Test completed successfully!")
    await Timer(200, units="ns")  # Final settling time
