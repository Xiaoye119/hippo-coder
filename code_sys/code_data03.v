module sync_fifo #(
    parameter DATA_WIDTH = 8,
    parameter FIFO_DEPTH = 16
)(
    input wire clk,          // 时钟信号
    input wire rst_n,        // 异步复位，低电平有效
    input wire wr_en,        // 写使能
    input wire rd_en,        // 读使能
    input wire [DATA_WIDTH-1:0] wr_data,  // 写数据
    output reg [DATA_WIDTH-1:0] rd_data,  // 读数据
    output wire full,        // 队列满标志
    output wire empty,       // 队列空标志
    output reg [$clog2(FIFO_DEPTH):0] count // 队列中的元素数量
);

    // FIFO 存储器
    reg [DATA_WIDTH-1:0] mem [0:FIFO_DEPTH-1];

    // 指针
    reg [$clog2(FIFO_DEPTH)-1:0] wr_ptr;
    reg [$clog2(FIFO_DEPTH)-1:0] rd_ptr;

    // 状态寄存器
    reg [FIFO_DEPTH:0] status;

    // 满和空标志
    assign full = (count == FIFO_DEPTH);
    assign empty = (count == 0);

    // 写操作
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wr_ptr <= 0;
            for (integer i = 0; i < FIFO_DEPTH; i = i + 1)
                mem[i] <= 0;
        end else if (wr_en && !full) begin
            mem[wr_ptr] <= wr_data;
            wr_ptr <= wr_ptr + 1;
        end
    end

    // 读操作
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rd_ptr <= 0;
            rd_data <= 0;
        end else if (rd_en && !empty) begin
            rd_data <= mem[rd_ptr];
            rd_ptr <= rd_ptr + 1;
        end
    end

    // 更新状态寄存器
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            count <= 0;
        end else begin
            if (wr_en && !full && !rd_en) begin
                count <= count + 1;
            end else if (rd_en && !empty && !wr_en) begin
                count <= count - 1;
            end
        end
    end

endmodule

// 测试模块
module tb_sync_fifo;
    reg clk;
    reg rst_n;
    reg wr_en;
    reg rd_en;
    reg [7:0] wr_data;
    wire [7:0] rd_data;
    wire full;
    wire empty;
    wire [4:0] count;

    // 实例化 FIFO
    sync_fifo #(.DATA_WIDTH(8), .FIFO_DEPTH(16)) uut (
        .clk(clk),
        .rst_n(rst_n),
        .wr_en(wr_en),
        .rd_en(rd_en),
        .wr_data(wr_data),
        .rd_data(rd_data),
        .full(full),
        .empty(empty),
        .count(count)
    );

    // 时钟生成
    initial begin
        clk = 0;
        forever #5 clk = ~clk;  // 10个时间单位为一个周期
    end

    // 测试序列
    initial begin
        // 初始化
        rst_n = 0;
        wr_en = 0;
        rd_en = 0;
        wr_data = 0;
        #20 rst_n = 1;

        // 写入数据
        for (integer i = 0; i < 16; i = i + 1) begin
            @(posedge clk);
            wr_en = 1;
            wr_data = i;
        end
        @(posedge clk);
        wr_en = 0;

        // 读取数据
        for (integer i = 0; i < 16; i = i + 1) begin
            @(posedge clk);
            rd_en = 1;
        end
        @(posedge clk);
        rd_en = 0;

        // 结束仿真
        $finish;
    end

    // 监控输出
    initial begin
        $monitor("Time=%0t | wr_en=%b, rd_en=%b, wr_data=%h, rd_data=%h, full=%b, empty=%b, count=%d",
                 $time, wr_en, rd_en, wr_data, rd_data, full, empty, count);
    end

endmodule