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

    output wire full,
    input wire r_en,
    output wire [WIDTH-1:0] r_data,
    output wire empty
);

    localparam ADDR_WIDTH = $clog2(DEPTH);

    reg [WIDTH-1:0] mem [0:DEPTH-1];

    // Write and read pointers (binary and gray code)
    reg [ADDR_WIDTH:0] wbin, wgray;
    reg [ADDR_WIDTH:0] rbin, rgray;

    // Synchronized gray pointers
    reg [ADDR_WIDTH:0] rgray_s1, rgray_s2;
    reg [ADDR_WIDTH:0] wgray_s1, wgray_s2;

    // Output register for r_data
    reg [WIDTH-1:0] rdata_reg;
    assign r_data = rdata_reg;

    /* ---------------------- Gray Code Conversion ---------------------- */
    function automatic [ADDR_WIDTH:0] bin2gray(input [ADDR_WIDTH:0] bin);
        bin2gray = bin ^ (bin >> 1);
    endfunction

    function automatic [ADDR_WIDTH:0] gray2bin(input [ADDR_WIDTH:0] gray);
        integer i;
        begin
            gray2bin[ADDR_WIDTH] = gray[ADDR_WIDTH];
            for (i = ADDR_WIDTH - 1; i >= 0; i = i - 1)
                gray2bin[i] = gray2bin[i+1] ^ gray[i];
        end
    endfunction

    /* ---------------------- Write Domain ---------------------- */
    wire [ADDR_WIDTH:0] rbin_s = gray2bin(rgray_s2);
    assign full = ((wgray[ADDR_WIDTH] != rgray_s2[ADDR_WIDTH]) &&
                   (wgray[ADDR_WIDTH-1:0] == rgray_s2[ADDR_WIDTH-1:0]));

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

    // Synchronize read pointer into write clock domain
    always @(posedge w_clk or posedge rst) begin
        if (rst) begin
            rgray_s1 <= 0;
            rgray_s2 <= 0;
        end else begin
            rgray_s1 <= rgray;
            rgray_s2 <= rgray_s1;
        end
    end

    /* ---------------------- Read Domain ---------------------- */
    wire [ADDR_WIDTH:0] wbin_s = gray2bin(wgray_s2);
    assign empty = (rgray == wgray_s2);

    always @(posedge r_clk or posedge rst) begin
        if (rst) begin
            rbin <= 0;
            rgray <= 0;
            rdata_reg <= 0;
        end else if (r_en && !empty) begin
            rdata_reg <= mem[rbin[ADDR_WIDTH-1:0]];
            rbin <= rbin + 1;
            rgray <= bin2gray(rbin + 1);
        end
    end

    // Synchronize write pointer into read clock domain
    always @(posedge r_clk or posedge rst) begin
        if (rst) begin
            wgray_s1 <= 0;
            wgray_s2 <= 0;
        end else begin
            wgray_s1 <= wgray;
            wgray_s2 <= wgray_s1;
        end
    end

endmodule
