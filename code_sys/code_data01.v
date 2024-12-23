 // ----------------------------------------------------------------------
// Copyright (c) 2016, The Regents of the University of California All
// rights reserved.
// 
// Redistribution and use in source and binary forms, with or without
// modification, are permitted provided that the following conditions are
// met:
// 
//     * Redistributions of source code must retain the above copyright
//       notice, this list of conditions and the following disclaimer.
// 
//     * Redistributions in binary form must reproduce the above
//       copyright notice, this list of conditions and the following
//       disclaimer in the documentation and/or other materials provided
//       with the distribution.
// 
//     * Neither the name of The Regents of the University of California
//       nor the names of its contributors may be used to endorse or
//       promote products derived from this software without specific
//       prior written permission.
// 
// THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
// "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
// LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
// A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL REGENTS OF THE
// UNIVERSITY OF CALIFORNIA BE LIABLE FOR ANY DIRECT, INDIRECT,
// INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
// BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS
// OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
// ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR
// TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE
// USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH
// DAMAGE.
// ----------------------------------------------------------------------
//----------------------------------------------------------------------------
// Filename:            ADM7V3_Gen3x4If128.v
// Version:             1.00.a
// Verilog Standard:    Verilog-2001
// Description:         Top level module for RIFFA 2.2 reference design for the
//                      the Xilinx 7V3 Development Board.
// Author:              Dustin Richmond (@darichmond)
//-----------------------------------------------------------------------------
`include "functions.vh"
`include "riffa.vh"
`include "ultrascale.vh"
`timescale 1ps / 1ps
module ADM7V3_Gen3x4If128
    #(// Number of RIFFA Channels
      parameter C_NUM_CHNL = 1,
      // Number of PCIe Lanes
      parameter C_NUM_LANES =  4,
      // Settings from Vivado IP Generator
      parameter C_PCI_DATA_WIDTH = 128,
      parameter C_MAX_PAYLOAD_BYTES = 256,
      parameter C_LOG_NUM_TAGS = 6) 
    (output [(C_NUM_LANES - 1) : 0] PCI_EXP_TXP,
     output [(C_NUM_LANES - 1) : 0] PCI_EXP_TXN,
     input [(C_NUM_LANES - 1) : 0]  PCI_EXP_RXP,
     input [(C_NUM_LANES - 1) : 0]  PCI_EXP_RXN,

     output [5:0]                   LED,
     input                          PCIE_REFCLK_P,
     input                          PCIE_REFCLK_N,
     input                          PCIE_RESET_N
     );

    // Clocks, etc
    wire                            user_lnk_up;
    wire                            user_clk;
    wire                            user_reset;
    wire                            pcie_refclk;
    wire                            pcie_reset_n;

    // Interface: RQ (TXC)
    wire                            s_axis_rq_tlast;
    wire [C_PCI_DATA_WIDTH-1:0]     s_axis_rq_tdata;
    wire [`SIG_RQ_TUSER_W-1:0]      s_axis_rq_tuser;
    wire [(C_PCI_DATA_WIDTH/32)-1:0] s_axis_rq_tkeep;
    wire                             s_axis_rq_tready;
    wire                             s_axis_rq_tvalid;
    // Interface: RC (RXC)
    wire [C_PCI_DATA_WIDTH-1:0]      m_axis_rc_tdata;
    wire [`SIG_RC_TUSER_W-1:0]       m_axis_rc_tuser;
    wire                             m_axis_rc_tlast;
    wire [(C_PCI_DATA_WIDTH/32)-1:0] m_axis_rc_tkeep;
    wire                             m_axis_rc_tvalid;
    wire                             m_axis_rc_tready;
    // Interface: CQ (RXR)
    wire [C_PCI_DATA_WIDTH-1:0]      m_axis_cq_tdata;
    wire [`SIG_CQ_TUSER_W-1:0]       m_axis_cq_tuser;
    wire                             m_axis_cq_tlast;
    wire [(C_PCI_DATA_WIDTH/32)-1:0] m_axis_cq_tkeep;
    wire                             m_axis_cq_tvalid;
    wire                             m_axis_cq_tready;
    // Interface: CC (TXC)
    wire [C_PCI_DATA_WIDTH-1:0]      s_axis_cc_tdata;
    wire [`SIG_CC_TUSER_W-1:0]       s_axis_cc_tuser;
    wire                             s_axis_cc_tlast;
    wire [(C_PCI_DATA_WIDTH/32)-1:0] s_axis_cc_tkeep;
    wire                             s_axis_cc_tvalid;
    wire                             s_axis_cc_tready;

    // Configuration (CFG) Interface                                           
    wire [3:0]                       pcie_rq_seq_num;
    wire                             pcie_rq_seq_num_vld;
    wire [5:0]                       pcie_rq_tag;
    wire                             pcie_rq_tag_vld;
    wire                             pcie_cq_np_req;
    wire [5:0]                       pcie_cq_np_req_count;

    wire                             cfg_phy_link_down;
    wire [3:0]                       cfg_negotiated_width; // CONFIG_LINK_WIDTH
    wire [2:0]                       cfg_current_speed; // CONFIG_LINK_RATE
    wire [2:0]                       cfg_max_payload; // CONFIG_MAX_PAYLOAD
    wire [2:0]                       cfg_max_read_req; // CONFIG_MAX_READ_REQUEST
    wire [7:0]                       cfg_function_status; // [2] = CONFIG_BUS_MASTER_ENABLE
    wire [5:0]                       cfg_function_power_state; // Ignorable but not removable
    wire [11:0]                      cfg_vf_status; // Ignorable but not removable
    wire [17:0]                      cfg_vf_power_state; // Ignorable but not removable
    wire [1:0]                       cfg_link_power_state; // Ignorable but not removable

    // Error Reporting Interface
    wire                             cfg_err_cor_out;
    wire                             cfg_err_nonfatal_out;
    wire                             cfg_err_fatal_out;

    wire                             cfg_ltr_enable;
    wire [5:0]                       cfg_ltssm_state;// TODO: Connect to LED's
    wire [1:0]                       cfg_rcb_status;
    wire [1:0]                       cfg_dpa_substate_change;
    wire [1:0]                       cfg_obff_enable;
    wire                             cfg_pl_status_change;

    wire [1:0]                       cfg_tph_requester_enable;
    wire [5:0]                       cfg_tph_st_mode;
    wire [5:0]                       cfg_vf_tph_requester_enable;
    wire [17:0]                      cfg_vf_tph_st_mode;
    wire [7:0]                       cfg_fc_ph;
    wire [11:0]                      cfg_fc_pd;
    wire [7:0]                       cfg_fc_nph;
    wire [11:0]                      cfg_fc_npd;
    wire [7:0]                       cfg_fc_cplh;
    wire [11:0]                      cfg_fc_cpld;
    wire [2:0]                       cfg_fc_sel;

    // Interrupt Interface Signals
    wire [3:0]                       cfg_interrupt_int;
    wire [1:0]                       cfg_interrupt_pending;
    wire                             cfg_interrupt_sent;
    wire [1:0]                       cfg_interrupt_msi_enable;
    wire [5:0]                       cfg_interrupt_msi_vf_enable;
    wire [5:0]                       cfg_interrupt_msi_mmenable;
    wire                             cfg_interrupt_msi_mask_update;
    wire [31:0]                      cfg_interrupt_msi_data;
    wire [3:0]                       cfg_interrupt_msi_select;
    wire [31:0]                      cfg_interrupt_msi_int;
    wire [63:0]                      cfg_interrupt_msi_pending_status;
    wire                             cfg_interrupt_msi_sent;
    wire                             cfg_interrupt_msi_fail;
    wire [2:0]                       cfg_interrupt_msi_attr;
    wire                             cfg_interrupt_msi_tph_present;
    wire [1:0]                       cfg_interrupt_msi_tph_type;
    wire [8:0]                       cfg_interrupt_msi_tph_st_tag;
    wire [2:0]                       cfg_interrupt_msi_function_number;

    wire                             rst_out;
    wire [C_NUM_CHNL-1:0]            chnl_rx_clk; 
    wire [C_NUM_CHNL-1:0]            chnl_rx; 
    wire [C_NUM_CHNL-1:0]            chnl_rx_ack; 
    wire [C_NUM_CHNL-1:0]            chnl_rx_last; 
    wire [(C_NUM_CHNL*`SIG_CHNL_LENGTH_W)-1:0] chnl_rx_len; 
    wire [(C_NUM_CHNL*`SIG_CHNL_OFFSET_W)-1:0] chnl_rx_off; 
    wire [(C_NUM_CHNL*C_PCI_DATA_WIDTH)-1:0]   chnl_rx_data; 
    wire [C_NUM_CHNL-1:0]                      chnl_rx_data_valid; 
    wire [C_NUM_CHNL-1:0]                      chnl_rx_data_ren;

    wire [C_NUM_CHNL-1:0]                      chnl_tx_clk; 
    wire [C_NUM_CHNL-1:0]                      chnl_tx; 
    wire [C_NUM_CHNL-1:0]                      chnl_tx_ack;
    wire [C_NUM_CHNL-1:0]                      chnl_tx_last; 
    wire [(C_NUM_CHNL*`SIG_CHNL_LENGTH_W)-1:0] chnl_tx_len; 
    wire [(C_NUM_CHNL*`SIG_CHNL_OFFSET_W)-1:0] chnl_tx_off; 
    wire [(C_NUM_CHNL*C_PCI_DATA_WIDTH)-1:0]   chnl_tx_data; 
    wire [C_NUM_CHNL-1:0]                      chnl_tx_data_valid; 
    wire [C_NUM_CHNL-1:0]                      chnl_tx_data_ren;

    genvar                                     chnl;

    IBUF 
        #()  
    pci_reset_n_ibuf 
        (.O(pcie_reset_n), 
         .I(PCIE_RESET_N));

    IBUFDS_GTE2 
        #()
    refclk_ibuf 
        (.O(pcie_refclk), 
         .ODIV2(), 