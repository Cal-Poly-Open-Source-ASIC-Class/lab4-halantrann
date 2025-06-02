`timescale 1ps/1ps

module asynch_fifo #(
    parameter WIDTH = 8,
    parameter DEPTH = 16
)(
    input wire w_clk,
    input wire r_clk,
    input wire w_en,
    input wire rst,  // Active-high reset
    input wire [WIDTH-1:0] w_data,

    output reg full,
    input wire r_en,
    output wire [WIDTH-1:0] r_data,
    output reg empty
);

    localparam ADDR_WIDTH = $clog2(DEPTH);

    reg [WIDTH-1:0] mem [0:DEPTH-1];

    // Write and read pointers (binary and gray code)
    reg [ADDR_WIDTH:0] wbin, wgray;
    reg [ADDR_WIDTH:0] rbin, rgray;

    // Synchronized gray pointers
    reg [ADDR_WIDTH:0] wgray_s1, wgray_s2;  // write gray sync'd to read domain
    reg [ADDR_WIDTH:0] rgray_s1, rgray_s2;  // read gray sync'd to write domain

    // Output data
    assign r_data = mem[rbin[ADDR_WIDTH-1:0]];

    /* ---------------------- Gray Code Conversion ---------------------- */
    function automatic [ADDR_WIDTH:0] bin2gray(input [ADDR_WIDTH:0] bin);
        bin2gray = bin ^ (bin >> 1);
    endfunction

    /* ---------------------- Write Domain ---------------------- */
    // Write pointer update
    always @(posedge w_clk or posedge rst) begin
        if (rst) begin
            wbin <= 0;
            wgray <= 0;
        end else if (w_en && !full) begin
            mem[wbin[ADDR_WIDTH-1:0]] <= w_data;
            wbin <= wbin + 1;
            wgray <= bin2gray(wbin + 1);
        end
    end

    // Synchronize read gray pointer to write clock domain
    always @(posedge w_clk or posedge rst) begin
        if (rst) begin
            rgray_s1 <= 0;
            rgray_s2 <= 0;
        end else begin
            rgray_s1 <= rgray;
            rgray_s2 <= rgray_s1;
        end
    end

    // Full flag generation - Fixed logic
    always @(posedge w_clk or posedge rst) begin
        if (rst) begin
            full <= 0;
        end else begin
            // Check if FIFO will be full after next write
            // The FIFO is full when the next write pointer (after increment) 
            // would equal the read pointer with MSB inverted
            full <= (bin2gray(wbin + 1) == {~rgray_s2[ADDR_WIDTH:ADDR_WIDTH-1], 
                                          rgray_s2[ADDR_WIDTH-2:0]});
        end
    end

    /* ---------------------- Read Domain ---------------------- */
    // Read pointer update
    always @(posedge r_clk or posedge rst) begin
        if (rst) begin
            rbin <= 0;
            rgray <= 0;
        end else if (r_en && !empty) begin
            rbin <= rbin + 1;
            rgray <= bin2gray(rbin + 1);
        end
    end

    // Synchronize write gray pointer to read clock domain
    always @(posedge r_clk or posedge rst) begin
        if (rst) begin
            wgray_s1 <= 0;
            wgray_s2 <= 0;
        end else begin
            wgray_s1 <= wgray;
            wgray_s2 <= wgray_s1;
        end
    end

    // Empty flag  
    always @(posedge r_clk or posedge rst) begin
        if (rst) begin
            empty <= 1;
        end else begin
            empty <= (rgray == wgray_s2);
        end
    end

endmodule