`timescale 1ns/1ps
`default_nettype none

module tb_sva_negative_s1;
    logic aclk;
    logic aresetn;

    logic [31:0] s0_wdata;
    logic [3:0]  s0_wstrb;
    logic        s0_wlast, s0_wvalid, s0_wready;

    logic [31:0] s1_wdata;
    logic [3:0]  s1_wstrb;
    logic        s1_wlast, s1_wvalid, s1_wready;

    initial begin
        aclk = 1'b0;
        forever #5 aclk = ~aclk;
    end

    axi4_crossbar_sva dut (
        .aclk(aclk),
        .aresetn(aresetn),
        .s0_wdata(s0_wdata),
        .s0_wstrb(s0_wstrb),
        .s0_wlast(s0_wlast),
        .s0_wvalid(s0_wvalid),
        .s0_wready(s0_wready),
        .s1_wdata(s1_wdata),
        .s1_wstrb(s1_wstrb),
        .s1_wlast(s1_wlast),
        .s1_wvalid(s1_wvalid),
        .s1_wready(s1_wready)
    );

    initial begin
        aresetn = 1'b0;
        s0_wdata = 32'b0;
        s0_wstrb = 4'hF;
        s0_wlast = 1'b0;
        s0_wvalid = 1'b0;
        s0_wready = 1'b0;

        s1_wdata = 32'b0;
        s1_wstrb = 4'hF;
        s1_wlast = 1'b0;
        s1_wvalid = 1'b0;
        s1_wready = 1'b0;

        #12;
        aresetn = 1'b1;

        @(negedge aclk);
        s1_wvalid = 1'b1;
        s1_wdata = 32'h12345678;

        @(negedge aclk);
        s1_wdata = 32'hDEADBEEF;

        repeat (3) @(negedge aclk);
        $display("ERROR: Expected S1 SVA assertion failure did not occur.");
        $finish;
    end
endmodule

`default_nettype wire
