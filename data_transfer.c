#include <Python.h>
#include <pthread.h>
#include <string.h>
#include <fcntl.h>
#include "spi.h"

// SPI全局变量
int spi_fd = -1;
struct_spi_param spi_param = {
    .speed = 3200000,
    .mode = 0,
    .data_bit = 8,
    .lsb_first = 0,
    .cs_high = 0,
    .no_cs = 0,
    .delay = 0,
    .dual_spi = 0,
    .quad_spi = 0
};

// 颜色状态全局变量
uint8_t current_r = 0;
uint8_t current_g = 0;
uint8_t current_b = 0;

// 互斥锁
pthread_mutex_t led_mutex = PTHREAD_MUTEX_INITIALIZER;

// 设置手势命令函数
static PyObject* set_gesture_command(PyObject* self, PyObject* args) {
    const char *command;
    
    // 解析一个字符串参数
    if (!PyArg_ParseTuple(args, "s", &command)) {
        return NULL; // 解析失败触发Python异常
    }
    
    // 打印接收到的命令
    printf("接收到手势命令: %s\n", command);
    
    // 使用互斥锁保护全局变量
    pthread_mutex_lock(&led_mutex);
    
    // 根据命令设置LED效果
    if (strcmp(command, "0") == 0) {
        // 绿色
        current_r = 0;
        current_g = 255;
        current_b = 0;
        printf("设置: 绿色\n");
    } else if (strcmp(command, "1") == 0) {
        // 蓝色
        current_r = 0;
        current_g = 0;
        current_b = 255;
        printf("设置: 蓝色\n");
    } else if (strcmp(command, "2") == 0) {
        // 红色
        current_r = 255;
        current_g = 0;
        current_b = 0;
        printf("设置: 红色\n");
    } else if (strcmp(command, "3") == 0) {
        // 白色
        current_r = 255;
        current_g = 255;
        current_b = 255;
        printf("设置: 白色\n");
    } else if (strcmp(command, "4") == 0) {
        // 青色
        current_r = 0;
        current_g = 255;
        current_b = 255;
        printf("设置: 青色\n");
    } else if (strcmp(command, "5") == 0) {
        // 粉色
        current_r = 255;
        current_g = 192;
        current_b = 203;
        printf("设置: 粉色\n");
    } else if (strcmp(command, "10") == 0) {
        // 无色
        current_r = 0;
        current_g = 0;
        current_b = 0;
        printf("设置: 关灯\n");
    } else {
        printf("未知手势命令: %s\n", command);
    }
    
    // 应用颜色设置
    ws2812b_set_color(spi_fd, spi_param, 30, current_r, current_g, current_b);
    
    pthread_mutex_unlock(&led_mutex);
    
    Py_RETURN_NONE;
}

// 初始化SPI设备
static PyObject* init_spi(PyObject* self, PyObject* args) {
    const char *device;
    
    // 解析设备路径参数
    if (!PyArg_ParseTuple(args, "s", &device)) {
        return NULL;
    }
    
    printf("打开SPI设备: %s\n", device);
    spi_fd = open(device, O_RDWR);
    if (spi_fd < 0) {
        perror(device);
        return Py_BuildValue("i", -1);
    }

    // 设置SPI参数
    if (func_set_opt(spi_fd, spi_param) < 0) {
        perror("SPI设置参数失败");
        close(spi_fd);
        return Py_BuildValue("i", -2);
    }
    
    // 初始化为关闭状态
    ws2812b_set_color(spi_fd, spi_param, 30, 0, 0, 0);
    
    return Py_BuildValue("i", 0);
}

// 清理资源
static PyObject* cleanup(PyObject* self, PyObject* args) {
    if (spi_fd >= 0) {
        // 关闭灯带
        ws2812b_set_color(spi_fd, spi_param, 30, 0, 0, 0);
        close(spi_fd);
        spi_fd = -1;
        printf("SPI设备已关闭\n");
    }
    Py_RETURN_NONE;
}

// 方法定义
static PyMethodDef DataMethods[] = {
    {"init_spi", init_spi, METH_VARARGS, "Initialize SPI device"},
    {"set_gesture_command", set_gesture_command, METH_VARARGS, "Set gesture command"},
    {"cleanup", cleanup, METH_VARARGS, "Clean up resources"},
    {NULL, NULL, 0, NULL}
};

// 定义模块
static struct PyModuleDef datamodule = {
    PyModuleDef_HEAD_INIT,
    "data_transfer",  // 模块名
    "Module for gesture control of WS2812B LEDs",  // 模块文档
    -1,               // 每个解释器实例保留一个模块实例
    DataMethods
};

PyMODINIT_FUNC PyInit_data_transfer(void) {
    return PyModule_Create(&datamodule);
}