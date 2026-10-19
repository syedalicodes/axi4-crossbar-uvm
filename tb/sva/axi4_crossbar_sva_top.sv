`default_nettype none

module axi4_crossbar_sva_top (
    input logic aclk,
    input logic aresetn,

    input logic [31:0] s0_wdata,
    input logic [3:0]  s0_wstrb,
    input logic        s0_wlast,
    input logic        s0_wvalid,
    input logic        s0_wready,

    input logic [31:0] s1_wdata,
    input logic [3:0]  s1_wstrb,
    input logic        s1_wlast,
    input logic        s1_wvalid,
    input logic        s1_wready
);

    axi4_crossbar_sva checks (
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

endmodule

`default_nettype wire
