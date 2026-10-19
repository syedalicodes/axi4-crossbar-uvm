`timescale 1ns/1ps
`default_nettype none
/* verilator lint_off SYNCASYNCNET */
module axi4_crossbar_sva (
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

    // If a write beat is stalled, its payload and VALID
    // must remain stable on the following clock.
    property p_s0_w_stable_when_stalled;
        @(posedge aclk) disable iff (!aresetn)
        (s0_wvalid && !s0_wready)
        |=> (s0_wvalid &&
             $stable(s0_wdata) &&
             $stable(s0_wstrb) &&
             $stable(s0_wlast));
    endproperty

    property p_s1_w_stable_when_stalled;
        @(posedge aclk) disable iff (!aresetn)
        (s1_wvalid && !s1_wready)
        |=> (s1_wvalid &&
             $stable(s1_wdata) &&
             $stable(s1_wstrb) &&
             $stable(s1_wlast));
    endproperty

    a_s0_w_stable_when_stalled:
        assert property (p_s0_w_stable_when_stalled);

    a_s1_w_stable_when_stalled:
        assert property (p_s1_w_stable_when_stalled);

endmodule

/* verilator lint_on SYNCASYNCNET */
`default_nettype wire
