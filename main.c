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
#include <pthread.h>
#include <sys/stat.h>   // 用于mkfifo
#include <fcntl.h>      // 用于open
#include "spi.h"

// 全局变量
int spi_fd;
int running = 1; // 控制程序运行的标志
int flashing = 0; // 闪烁状态标志
int flash_active = 0; // 当前闪烁是否激活
int flash_speed = 2; // 闪烁速度等级 (1-慢, 2-中, 3-快)
pthread_t input_thread_id;
pthread_t flash_thread_id;
int fifo_fd;
char fifo_path[] = "/tmp/gesture_fifo";
pthread_t gesture_thread_id;
pthread_mutex_t led_mutex = PTHREAD_MUTEX_INITIALIZER; // 互斥锁

// SPI参数配置
struct_spi_param spi_param = {
    .speed = 3200000,   // 降低为3.2MHz以提高稳定性
    .mode = 0,          // SPI模式0
    .data_bit = 8,      // 8位数据
    .lsb_first = 0,     // MSB先发
    .cs_high = 0,
    .no_cs = 0,         // 不使用SPI_NO_CS标志
    .delay = 0,
    .dual_spi = 0,
    .quad_spi = 0
};

char dev[20] = "/dev/spidev0.0"; // 默认SPI设备

// 当前颜色状态
uint8_t current_r = 0;
uint8_t current_g = 0;
uint8_t current_b = 0;

// 闪烁颜色状态
uint8_t flash_r = 0;
uint8_t flash_g = 0;
uint8_t flash_b = 0;

// 闪烁控制线程
void *flash_thread(void *arg) {
    while (running) {
        if (flashing) {
            flash_active = 1;
            
            // 亮灯（所有LED）
            ws2812b_set_color(spi_fd, spi_param, 30, flash_r, flash_g, flash_b);
            
            // 根据速度设置延迟
            int delay_ms;
            switch (flash_speed) {
                case 1: delay_ms = 1000; break; // 慢速: 1秒
                case 2: delay_ms = 500; break;  // 中速: 0.5秒
                case 3: delay_ms = 250; break;  // 快速: 0.25秒
                default: delay_ms = 500; break;
            }
            usleep(delay_ms * 1000);
            
            // 灭灯（所有LED）
            ws2812b_set_color(spi_fd, spi_param, 30, 0, 0, 0);
            usleep(delay_ms * 1000);
        } else {
            if (flash_active) {
                // 停止闪烁后恢复当前颜色
                ws2812b_set_color(spi_fd, spi_param, 30, current_r, current_g, current_b);
                flash_active = 0;
            }
            usleep(100000); // 100ms延迟，减少CPU使用率
        }
    }
    return NULL;
}

// 线程函数：处理用户输入
void *input_thread(void *arg) {
    printf("\nWS2812B LED 控制菜单 (GRB格式):\n");
    printf("  0 - 红色 (Red)\n");
    printf("  1 - 绿色 (Green)\n");
    printf("  2 - 蓝色 (Blue)\n");
    printf("  3 - 青色 (Cyan)\n");
    printf("  4 - 洋红色 (Magenta)\n");
    printf("  5 - 黄色 (Yellow)\n");
    printf("  6 - 白色 (White)\n");
    printf("  7 - 紫色 (Purple)\n");
    printf("  8 - 橙色 (Orange)\n");
    printf("  9 - 粉色 (Pink)\n");
    printf("  o - 关闭所有LED (Off)\n");
    printf("  b - 开始/停止闪烁 (Blink)\n");
    printf("  s - 设置闪烁速度 (Speed)\n");
    printf("  r - 修复第一个LED问题 (修复信号时序)\n");
    printf("  q - 退出程序 (Quit)\n");
    printf("请输入选择: ");
    
    while (running) {
        char input = getchar();
        
        switch (input) {
            case '0': // 红色
                current_r = 255;
                current_g = 0;
                current_b = 0;
                printf("\n设置颜色: 红色 (GRB: G=0, R=255, B=0)\n");
                break;
                
            case '1': // 绿色
                current_r = 0;
                current_g = 255;
                current_b = 0;
                printf("\n设置颜色: 绿色 (GRB: G=255, R=0, B=0)\n");
                break;
                
            case '2': // 蓝色
                current_r = 0;
                current_g = 0;
                current_b = 255;
                printf("\n设置颜色: 蓝色 (GRB: G=0, R=0, B=255)\n");
                break;
                
            case '3': // 青色
                current_r = 0;
                current_g = 255;
                current_b = 255;
                printf("\n设置颜色: 青色 (GRB: G=255, R=0, B=255)\n");
                break;
                
            case '4': // 洋红色
                current_r = 255;
                current_g = 0;
                current_b = 255;
                printf("\n设置颜色: 洋红色 (GRB: G=0, R=255, B=255)\n");
                break;
                
            case '5': // 黄色
                current_r = 255;
                current_g = 255;
                current_b = 0;
                printf("\n设置颜色: 黄色 (GRB: G=255, R=255, B=0)\n");
                break;
                
            case '6': // 白色
                current_r = 255;
                current_g = 255;
                current_b = 255;
                printf("\n设置颜色: 白色 (GRB: G=255, R=255, B=255)\n");
                break;
                
            case '7': // 紫色
                  current_r = 128;
                current_g = 0;
                current_b = 128;
                printf("\n设置颜色: 紫色 (GRB: G=0, R=128, B=128)\n");
                break;
                
            case '8': // 橙色
                current_r = 255;
                current_g = 165;
                current_b = 0;
                printf("\n设置颜色: 橙色 (GRB: G=165, R=255, B=0)\n");
                break;
                
            case '9': // 粉色
                current_r = 255;
                current_g = 192;
                current_b = 203;
                printf("\n设置颜色: 粉色 (GRB: G=192, R=255, B=203)\n");
                break;
                
            case 'o': // 关闭
                current_r = 0;
                current_g = 0;
                current_b = 0;
                flashing = 0; // 停止闪烁
                printf("\n关闭所有LED\n");
                break;
                
            case 'b': // 开始/停止闪烁
                if (flashing) {
                    flashing = 0;
                    printf("\n停止闪烁\n");
                } else {
                    // 保存当前颜色为闪烁颜色
                    flash_r = current_r;
                    flash_g = current_g;
                    flash_b = current_b;
                    
                    // 避免在黑色状态下闪烁
                    if (flash_r == 0 && flash_g == 0 && flash_b == 0) {
                        printf("\n当前颜色为黑色，无法闪烁！\n");
                    } else {
                        flashing = 1;
                        printf("\n开始闪烁当前颜色\n");
                    }
                }
                break;
                
            case 's': // 设置闪烁速度
                printf("\n当前闪烁速度: %d (1-慢, 2-中, 3-快)\n", flash_speed);
                printf("设置新速度 (1-3): ");
                char speed_input = getchar();
                if (speed_input >= '1' && speed_input <= '3') {
                    flash_speed = speed_input - '0';
                    printf("\n闪烁速度设置为: %d\n", flash_speed);
                } else {
                    printf("\n无效的速度设置!\n");
                }
                // 清除输入缓冲区
                int c;
                while ((c = getchar()) != '\n' && c != EOF);
                break;
                
            case 'r': // 修复第一个LED信号问题
                // 发送额外的复位信号来稳定第一个LED
                printf("\n正在修复第一个LED信号问题...\n");
                int fix_reset_size = 800;  // 约125µs复位信号
                unsigned char *fix_reset_tx = calloc(fix_reset_size, sizeof(char));
                if (fix_reset_tx) {
                    func_transfer(spi_fd, fix_reset_tx, NULL, fix_reset_size, spi_param);
                    free(fix_reset_tx);
                    printf("修复信号已完成\n");
                }
                break;
                
            case 'q': // 退出
                running = 0;
                printf("\n正在退出程序...\n");
                break;
                
            case '\n': // 忽略回车
                break;
                
            default:
                printf("\n无效输入! 有效选项: 0-9, o, b, s, r, q\n");
                break;
        }
        
        // 清除输入缓冲区
        if (input != '\n') {
            int c;
            while ((c = getchar()) != '\n' && c != EOF);
        }
        
        if (running && input != '\n') {
            printf("请输入下一个选择: ");
            fflush(stdout);
        }
    }
    
    return NULL;
}

int main(int argc, char *argv[])
{
    if (argc > 1) {
        snprintf(dev, sizeof(dev), "/dev/%s", argv[1]);
    }

    printf("打开SPI设备: %s\n", dev);
    spi_fd = open(dev, O_RDWR);
    if (spi_fd < 0) {
        perror(dev);
        printf("无法打开SPI设备 %s \n", dev);
        exit(1);
    }

    // 设置SPI参数
    if (func_set_opt(spi_fd, spi_param) < 0) {
        perror("SPI设置参数失败");
        close(spi_fd);
        exit(1);
    }

    // 创建输入线程
    if (pthread_create(&input_thread_id, NULL, input_thread, NULL) != 0) {
        perror("创建输入线程失败");
        close(spi_fd);
        exit(1);
    }

    // 创建闪烁线程
    if (pthread_create(&flash_thread_id, NULL, flash_thread, NULL) != 0) {
        perror("创建闪烁线程失败");
        close(spi_fd);
        exit(1);
    }

    printf("启动WS2812B控制 (30个LED)...\n");
    printf("按 'q' 退出程序\n");
    
    // 主循环 - 根据用户输入更新LED颜色
    while (running) {
        if (!flashing) {
            ws2812b_set_color(spi_fd, spi_param, 30, 
                             current_r, current_g, current_b);
        }
        usleep(100000); // 100ms延迟，减少CPU使用率
    }

    // 清理：关闭灯带
    ws2812b_set_color(spi_fd, spi_param, 30, 0, 0, 0);
    
    // 等待线程结束
    pthread_join(input_thread_id, NULL);
    pthread_join(flash_thread_id, NULL);
    
    close(spi_fd);
    printf("程序已退出\n");
    return 0;
}