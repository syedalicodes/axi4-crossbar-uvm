`default_nettype none

module axi4_addr_decode #(
    parameter int ADDR_WIDTH = 32,
    parameter logic [ADDR_WIDTH-1:0] BASE0 = 32'h0000_0000,
    parameter logic [ADDR_WIDTH-1:0] BASE1 = 32'h0000_1000,
    parameter logic [ADDR_WIDTH-1:0] REGION_SIZE = 32'h0000_1000
) (
    input  logic [ADDR_WIDTH-1:0] addr,
    output logic                  decode_valid,
    output logic                  slave_sel,
    output logic                  decode_error
);

    logic hit0;
    logic hit1;

    // Avoid an always-true unsigned comparison when BASE0 is zero.
    generate
        if (BASE0 == {ADDR_WIDTH{1'b0}}) begin : g_base0_zero
            always_comb begin
                hit0 = (addr < REGION_SIZE);
            end
        end else begin : g_base0_nonzero
            always_comb begin
                hit0 = (addr >= BASE0) &&
                       ((addr - BASE0) < REGION_SIZE);
            end
        end
    endgenerate

    always_comb begin
        hit1 = (addr >= BASE1) &&
               ((addr - BASE1) < REGION_SIZE);
    end

    // Region 0 has priority if the configured regions overlap.
    always_comb begin
        decode_valid = 1'b0;
        slave_sel    = 1'b0;
        decode_error = 1'b1;

        if (hit0) begin
            decode_valid = 1'b1;
            slave_sel    = 1'b0;
            decode_error = 1'b0;
        end else if (hit1) begin
            decode_valid = 1'b1;
            slave_sel    = 1'b1;
            decode_error = 1'b0;
        end
    end

endmodule

`default_nettype wire
