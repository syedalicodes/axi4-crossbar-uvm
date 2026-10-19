`default_nettype none

module axi4_crossbar_2x2 #(
    parameter int ADDR_WIDTH = 32,
    parameter int ID_WIDTH   = 4,
    parameter int DATA_WIDTH = 32,

    parameter logic [ADDR_WIDTH-1:0] S0_BASE = 32'h0000_0000,
    parameter logic [ADDR_WIDTH-1:0] S1_BASE = 32'h0000_1000,
    parameter logic [ADDR_WIDTH-1:0] REGION_SIZE = 32'h0000_1000
) (
    input logic aclk,
    input logic aresetn,

    // Master 0: write address
    input  logic [ID_WIDTH-1:0]   m0_awid,
    input  logic [ADDR_WIDTH-1:0] m0_awaddr,
    input  logic [7:0]            m0_awlen,
    input  logic [2:0]            m0_awsize,
    input  logic [1:0]            m0_awburst,
    input  logic                  m0_awvalid,
    output logic                  m0_awready,

    // Master 1: write address
    input  logic [ID_WIDTH-1:0]   m1_awid,
    input  logic [ADDR_WIDTH-1:0] m1_awaddr,
    input  logic [7:0]            m1_awlen,
    input  logic [2:0]            m1_awsize,
    input  logic [1:0]            m1_awburst,
    input  logic                  m1_awvalid,
    output logic                  m1_awready,

    // Slave 0: write address
    output logic [ID_WIDTH-1:0]   s0_awid,
    output logic [ADDR_WIDTH-1:0] s0_awaddr,
    output logic [7:0]            s0_awlen,
    output logic [2:0]            s0_awsize,
    output logic [1:0]            s0_awburst,
    output logic                  s0_awvalid,
    input  logic                  s0_awready,

    // Slave 1: write address
    output logic [ID_WIDTH-1:0]   s1_awid,
    output logic [ADDR_WIDTH-1:0] s1_awaddr,
    output logic [7:0]            s1_awlen,
    output logic [2:0]            s1_awsize,
    output logic [1:0]            s1_awburst,
    output logic                  s1_awvalid,
    input  logic                  s1_awready,

    // Master 0: write data
    input  logic [DATA_WIDTH-1:0]   m0_wdata,
    input  logic [DATA_WIDTH/8-1:0] m0_wstrb,
    input  logic                    m0_wlast,
    input  logic                    m0_wvalid,
    output logic                    m0_wready,

    // Master 1: write data
    input  logic [DATA_WIDTH-1:0]   m1_wdata,
    input  logic [DATA_WIDTH/8-1:0] m1_wstrb,
    input  logic                    m1_wlast,
    input  logic                    m1_wvalid,
    output logic                    m1_wready,

    // Slave 0: write data
    output logic [DATA_WIDTH-1:0]   s0_wdata,
    output logic [DATA_WIDTH/8-1:0] s0_wstrb,
    output logic                    s0_wlast,
    output logic                    s0_wvalid,
    input  logic                    s0_wready,

    // Slave 1: write data
    output logic [DATA_WIDTH-1:0]   s1_wdata,
    output logic [DATA_WIDTH/8-1:0] s1_wstrb,
    output logic                    s1_wlast,
    output logic                    s1_wvalid,
    input  logic                    s1_wready,

    // Diagnostic flags: asserted when WLAST mismatches AWLEN.
    output logic                    s0_wlast_error,
    output logic                    s1_wlast_error
);

    logic m0_hit_s0, m0_hit_s1;
    logic m1_hit_s0, m1_hit_s1;

    // One write burst per master and one active W owner per slave.
    logic m0_write_active, m1_write_active;

    logic s0_busy, s1_busy;
    logic s0_owner, s1_owner;
    logic s0_aw_from_m1, s1_aw_from_m1;

    // Number of write beats remaining after the current beat.
    // AXI AWLEN encodes beats minus one.
    logic [7:0] s0_beats_remaining, s1_beats_remaining;

    // Address-region decoding.
    generate
        if (S0_BASE == {ADDR_WIDTH{1'b0}}) begin : g_s0_zero
            always_comb begin
                m0_hit_s0 = (m0_awaddr < REGION_SIZE);
                m1_hit_s0 = (m1_awaddr < REGION_SIZE);
            end
        end else begin : g_s0_nonzero
            always_comb begin
                m0_hit_s0 = (m0_awaddr >= S0_BASE) &&
                            ((m0_awaddr - S0_BASE) < REGION_SIZE);
                m1_hit_s0 = (m1_awaddr >= S0_BASE) &&
                            ((m1_awaddr - S0_BASE) < REGION_SIZE);
            end
        end
    endgenerate

    always_comb begin
        m0_hit_s1 = (m0_awaddr >= S1_BASE) &&
                    ((m0_awaddr - S1_BASE) < REGION_SIZE);
        m1_hit_s1 = (m1_awaddr >= S1_BASE) &&
                    ((m1_awaddr - S1_BASE) < REGION_SIZE);
    end

    // AW routing. Master 0 has priority when both eligible masters
    // request the same idle slave. AW is accepted only when READY
    // is high and both the master and destination slave are available.
    always_comb begin
        m0_awready = 1'b0;
        m1_awready = 1'b0;
        s0_aw_from_m1 = 1'b0;
        s1_aw_from_m1 = 1'b0;

        s0_awid    = '0;
        s0_awaddr  = '0;
        s0_awlen   = '0;
        s0_awsize  = '0;
        s0_awburst = '0;
        s0_awvalid = 1'b0;

        s1_awid    = '0;
        s1_awaddr  = '0;
        s1_awlen   = '0;
        s1_awsize  = '0;
        s1_awburst = '0;
        s1_awvalid = 1'b0;

        if (aresetn && !s0_busy) begin
            if (m0_awvalid && m0_hit_s0 && !m0_write_active) begin
                s0_awid    = m0_awid;
                s0_awaddr  = m0_awaddr;
                s0_awlen   = m0_awlen;
                s0_awsize  = m0_awsize;
                s0_awburst = m0_awburst;
                s0_awvalid = 1'b1;
                m0_awready = s0_awready;
            end else if (m1_awvalid && m1_hit_s0 &&
                         !m1_write_active) begin
                s0_awid    = m1_awid;
                s0_awaddr  = m1_awaddr;
                s0_awlen   = m1_awlen;
                s0_awsize  = m1_awsize;
                s0_awburst = m1_awburst;
                s0_awvalid = 1'b1;
                m1_awready = s0_awready;
                s0_aw_from_m1 = 1'b1;
            end
        end

        if (aresetn && !s1_busy) begin
            if (m0_awvalid && m0_hit_s1 && !m0_write_active) begin
                s1_awid    = m0_awid;
                s1_awaddr  = m0_awaddr;
                s1_awlen   = m0_awlen;
                s1_awsize  = m0_awsize;
                s1_awburst = m0_awburst;
                s1_awvalid = 1'b1;
                m0_awready = s1_awready;
            end else if (m1_awvalid && m1_hit_s1 &&
                         !m1_write_active) begin
                s1_awid    = m1_awid;
                s1_awaddr  = m1_awaddr;
                s1_awlen   = m1_awlen;
                s1_awsize  = m1_awsize;
                s1_awburst = m1_awburst;
                s1_awvalid = 1'b1;
                m1_awready = s1_awready;
                s1_aw_from_m1 = 1'b1;
            end
        end
    end

    // W routing follows the destination latched at AW handshake.
    // WREADY remains low until a corresponding AW has been accepted.
    always_comb begin
        m0_wready = 1'b0;
        m1_wready = 1'b0;

        s0_wdata  = '0;
        s0_wstrb  = '0;
        s0_wlast  = 1'b0;
        s0_wvalid = 1'b0;

        s1_wdata  = '0;
        s1_wstrb  = '0;
        s1_wlast  = 1'b0;
        s1_wvalid = 1'b0;

        if (aresetn && s0_busy) begin
            if (!s0_owner) begin
                s0_wdata  = m0_wdata;
                s0_wstrb  = m0_wstrb;
                s0_wlast  = m0_wlast;
                s0_wvalid = m0_wvalid;
                m0_wready = s0_wready;
            end else begin
                s0_wdata  = m1_wdata;
                s0_wstrb  = m1_wstrb;
                s0_wlast  = m1_wlast;
                s0_wvalid = m1_wvalid;
                m1_wready = s0_wready;
            end
        end

        if (aresetn && s1_busy) begin
            if (!s1_owner) begin
                s1_wdata  = m0_wdata;
                s1_wstrb  = m0_wstrb;
                s1_wlast  = m0_wlast;
                s1_wvalid = m0_wvalid;
                m0_wready = s1_wready;
            end else begin
                s1_wdata  = m1_wdata;
                s1_wstrb  = m1_wstrb;
                s1_wlast  = m1_wlast;
                s1_wvalid = m1_wvalid;
                m1_wready = s1_wready;
            end
        end
    end

    // Capture destination on AW handshake. Release the master and slave
    // W-path ownership only after the final W beat handshakes.
    always_ff @(posedge aclk or negedge aresetn) begin
        if (!aresetn) begin
            m0_write_active <= 1'b0;
            m1_write_active <= 1'b0;
            s0_busy         <= 1'b0;
            s1_busy         <= 1'b0;
            s0_owner        <= 1'b0;
            s1_owner        <= 1'b0;
            s0_beats_remaining <= 8'd0;
            s1_beats_remaining <= 8'd0;
            s0_wlast_error <= 1'b0;
            s1_wlast_error <= 1'b0;
        end else begin
            if (s0_awvalid && s0_awready) begin
                s0_busy <= 1'b1;
                s0_beats_remaining <= s0_awlen;
                if (!s0_aw_from_m1) begin
                    m0_write_active <= 1'b1;
                    s0_owner        <= 1'b0;
                end else begin
                    m1_write_active <= 1'b1;
                    s0_owner        <= 1'b1;
                end
            end

            if (s1_awvalid && s1_awready) begin
                s1_busy <= 1'b1;
                s1_beats_remaining <= s1_awlen;
                if (!s1_aw_from_m1) begin
                    m0_write_active <= 1'b1;
                    s1_owner        <= 1'b0;
                end else begin
                    m1_write_active <= 1'b1;
                    s1_owner        <= 1'b1;
                end
            end

            // Check WLAST on each accepted beat. AWLEN is beats minus one.
            // Flags remain set until reset if WLAST mismatches the expected
            // final-beat position.
            if (s0_wvalid && s0_wready) begin
                if (s0_wlast != (s0_beats_remaining == 8'd0))
                    s0_wlast_error <= 1'b1;
            end

            if (s1_wvalid && s1_wready) begin
                if (s1_wlast != (s1_beats_remaining == 8'd0))
                    s1_wlast_error <= 1'b1;
            end

            // Release ownership when the expected final beat handshakes.
            if (s0_wvalid && s0_wready) begin
                if (s0_beats_remaining == 8'd0) begin
                    s0_busy <= 1'b0;
                    if (!s0_owner)
                        m0_write_active <= 1'b0;
                    else
                        m1_write_active <= 1'b0;
                end else begin
                    s0_beats_remaining <= s0_beats_remaining - 1'b1;
                end
            end

            if (s1_wvalid && s1_wready) begin
                if (s1_beats_remaining == 8'd0) begin
                    s1_busy <= 1'b0;
                    if (!s1_owner)
                        m0_write_active <= 1'b0;
                    else
                        m1_write_active <= 1'b0;
                end else begin
                    s1_beats_remaining <= s1_beats_remaining - 1'b1;
                end
            end
        end
    end


`ifndef SYNTHESIS
    // Simulation-only assertions for slave write-channel stability.
    axi4_crossbar_sva u_axi4_crossbar_sva (
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
`endif

endmodule

`default_nettype wire
