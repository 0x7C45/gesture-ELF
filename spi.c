#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <termios.h>
#include <sys/ioctl.h>
#include <linux/types.h>
#include <linux/spi/spidev.h>
#include "spi.h"

int func_set_opt(int fd, struct_spi_param param)
{
    int ret = 0;
    unsigned int set_mode = 0;

    // 只设置支持的模式位
    set_mode |= param.mode;
    if (1 == param.lsb_first) set_mode |= SPI_LSB_FIRST;
    if (1 == param.cs_high) set_mode |= SPI_CS_HIGH;
    
    if (1 == param.dual_spi) set_mode |= (SPI_TX_DUAL | SPI_RX_DUAL);
    else if (1 == param.quad_spi) set_mode |= (SPI_TX_QUAD | SPI_RX_QUAD);

    ret = ioctl(fd, SPI_IOC_WR_MODE, &set_mode);
    if (ret == -1) perror("SPI_IOC_WR_MODE failed");

    ret = ioctl(fd, SPI_IOC_RD_MODE, &set_mode);
    if (ret == -1) perror("SPI_IOC_RD_MODE failed");

    ret = ioctl(fd, SPI_IOC_WR_MAX_SPEED_HZ, &param.speed);
    if (ret == -1) perror("SPI_IOC_WR_MAX_SPEED_HZ failed");

    ret = ioctl(fd, SPI_IOC_RD_MAX_SPEED_HZ, &param.speed);
    if (ret == -1) perror("SPI_IOC_RD_MAX_SPEED_HZ failed");

    ret = ioctl(fd, SPI_IOC_WR_BITS_PER_WORD, &param.data_bit);
    if (ret == -1) perror("SPI_IOC_WR_BITS_PER_WORD failed");

    ret = ioctl(fd, SPI_IOC_RD_BITS_PER_WORD, &param.data_bit);
    if (ret == -1) perror("SPI_IOC_RD_BITS_PER_WORD failed");

    printf("SPI设置完成! 模式: 0x%x, 速率: %ld Hz, 位宽: %d\n", 
           set_mode, param.speed, param.data_bit);
    return 0;
}

void func_transfer(int fd, unsigned char *tx, unsigned char *rx, unsigned int lens, struct_spi_param param)
{
    int ret;
    struct spi_ioc_transfer tr = {
        .tx_buf = (unsigned long)tx,
        .rx_buf = (unsigned long)rx,
        .len = lens,
        .delay_usecs = param.delay,
        .speed_hz = param.speed,
        .bits_per_word = param.data_bit,
    };

    ret = ioctl(fd, SPI_IOC_MESSAGE(1), &tr);
    if (ret < 1) perror("SPI_IOC_MESSAGE失败");
}

// WS2812B设置颜色 - 使用GRB格式
void ws2812b_set_color(int fd, struct_spi_param param, 
                      int led_count, uint8_t r, uint8_t g, uint8_t b)
{
    
    // 在数据发送前添加稳定信号
    int stabilization_size = 50;
    unsigned char *stabilization_tx = calloc(stabilization_size, sizeof(char));
    if (stabilization_tx) {
        func_transfer(fd, stabilization_tx, NULL, stabilization_size, param);
        free(stabilization_tx);
    }
    
    // 每个LED需要24位数据(GRB顺序)
    int total_bits = led_count * 24;
    int buffer_size = total_bits;
    unsigned char *tx_buffer = malloc(buffer_size);
    if (!tx_buffer) {
        perror("为tx_buffer分配内存失败");
        return;
    }
    
    // 颜色数据转换为比特流(GRB顺序)
    // WS2812B使用GRB格式: 绿色(G), 红色(R), 蓝色(B)
    uint32_t grb_color = ((uint32_t)g << 16) | ((uint32_t)r << 8) | b;
    
    int buffer_index = 0;
    for (int i = 0; i < led_count; i++) {
        // 处理24位颜色数据(从高位到低位)
        for (int bit = 23; bit >= 0; bit--) {
            int color_bit = (grb_color >> bit) & 1;
            // 根据比特值选择编码
            tx_buffer[buffer_index++] = (color_bit == 1) ? 0xFC : 0xC0;
        }
    }
    
    // 1. 发送起始复位码（确保信号稳定）
    int start_reset_size = 100;  // 100 * 0.15625µs ≈ 15.6µs
    unsigned char *start_reset_tx = calloc(start_reset_size, sizeof(char));
    if (start_reset_tx) {
        func_transfer(fd, start_reset_tx, NULL, start_reset_size, param);
        free(start_reset_tx);
    }
    
    // 2. 发送LED数据
    func_transfer(fd, tx_buffer, NULL, buffer_size, param);
    
    // 3. 发送结束复位码(>50µs低电平)
    int end_reset_size = 400;  // 400 * 0.15625µs ≈ 62.5µs
    unsigned char *end_reset_tx = calloc(end_reset_size, sizeof(char));
    if (end_reset_tx) {
        func_transfer(fd, end_reset_tx, NULL, end_reset_size, param);
        free(end_reset_tx);
    }
    
    // 清理资源
    free(tx_buffer);
}