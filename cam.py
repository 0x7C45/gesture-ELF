import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import cv2
import threading
import queue
import os
from ultralytics import YOLO
import time
import data_transfer  # 导入我们创建的Python模块

# 全局变量
name = ""
model = YOLO(r'best.pt')
SPI_DEVICE = "/dev/spidev4.0"  # SPI设备路径

# 手势到颜色的映射
GESTURE_COLORS = {
    "0": (0, 255, 0),       # 绿色
    "1": (0, 0, 255),       # 蓝色
    "2": (255, 0, 0),       # 红色
    "3": (255, 255, 255),   # 白色
    "4": (0, 255, 255),     # 青色
    "5": (255, 192, 203),   # 紫色
    "10": (0, 0, 0)         # 无色
}
class ImageButton:
    def __init__(self, parent, size, normal_img, command=None):
        self.parent = parent
        self.size = size
        self.command = command
        
        # 创建透明画布
        self.canvas = tk.Canvas(parent, width=size, height=size, borderwidth=0,relief=tk.FLAT,
                              highlightthickness=0, bg='white')
        self.canvas.pack_propagate(False)  # 禁止自动调整大小
         # 改用grid布局
        self.canvas.grid(sticky="nsew")
        
        # 加载并调整图片
        try:
            self.photo = ImageTk.PhotoImage(Image.open(normal_img).resize((size, size)))
        except Exception as e:
            print(f"图片加载失败: {str(e)}")
            self.photo = None
        
        # 创建按钮
        if self.photo:
            self.button = tk.Button(
                self.canvas, 
                image=self.photo,
                command=self._on_click,
                bd=0,  # 去除边框
                highlightthickness=0
            )
            self.button.pack(expand=True)

    def _on_click(self):
        """点击事件处理"""
        if self.command and self.photo:
            self.command()
class CameraApp:
    def __init__(self, root):
        self.root = root
        self.root.title("摄像头集成界面")
        self.root.geometry("1980x1080")
        self.root.configure(bg='#FFFFFF')
         # 配置 grid 布局
        self.configure_layout()
        # 初始化摄像头
        self.cap = None
        self.try_open_camera()
        
        # 配置队列和线程
        self.frame_queue = queue.Queue(maxsize=2)
        self.running = False
        self.thread = None

        self.init_spi()

        # 自动启动预览
        if self.cap:
            self.start_capture()

        self.root.after(2000, self._auto_capture_loop)

        self.init_spi()
    
    def init_spi(self):
        """初始化SPI设备"""
        result = data_transfer.init_spi(SPI_DEVICE)
        if result != 0:
            print(f"SPI初始化失败，错误代码: {result}")
            self.show_status("SPI初始化失败")
        else:
            print("SPI初始化成功")
        

    def try_open_camera(self):
        """尝试打开摄像头"""
        try:
            self.cap = cv2.VideoCapture(11)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 480)

            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.cap.set(4, 640)
            if not self.cap.isOpened():
                raise Exception("无法打开摄像头")
            print(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            print(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        except Exception as e:
            print(f"摄像头错误: {str(e)}")
            self.cap = None

    def configure_layout(self):
        """配置左右分屏布局"""
        # 主窗口布局
        self.root.grid_columnconfigure(0, weight=3)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        # 视频显示区域
        self.video_frame = tk.Label(self.root, bg='#FFFFFF')
        self.video_frame.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")
        
        # self.video_frame.config(width=480, height=640)

        # self.status_frame = tk.Frame(self.root)
        # self.status_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        
        # self.logo_frame = tk.Frame(self.root,bg="#FFFFFF")
        # self.logo_frame.grid(row=1, column=1, padx=10, pady=10, sticky="e")
        
        
       
        # 控制面板
        control_panel = tk.Frame(self.root, bg='#FFFFFF')
        control_panel.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        
        # 控制面板列配置
        control_panel.grid_columnconfigure(0, weight=3)
        control_panel.grid_columnconfigure(1, weight=1)
        
        control_panel.grid_rowconfigure(0, weight=1)
        control_panel.grid_rowconfigure(1, weight=3)
        control_panel.grid_rowconfigure(2, weight=3)
        
        img1 = Image.open("logo.jpg")
        img1 = img1.resize((466, 127), Image.Resampling.LANCZOS)
        self.tk_img1 = ImageTk.PhotoImage(img1)
        lbl1 = ttk.Label(control_panel, image=self.tk_img1, borderwidth=0,background="#FFFFFF")
        lbl1.grid(row=0, column=1, columnspan=2,padx=10, pady=10, sticky="nsew")

        self.status_label = ttk.Label(
            control_panel,
            text="等待截图...",
            foreground="green",
            width=20,
            anchor="w"
        )
        self.status_label.grid(row=2, column=1, padx=10, pady=10, sticky="nsew")

        img2= Image.open("symbol.jpg")
        img2 = img2.resize((70, 70), Image.Resampling.LANCZOS)
        self.tk_img2 = ImageTk.PhotoImage(img2)
        lbl2 = ttk.Label(control_panel, image=self.tk_img2, borderwidth=0,background="#FFFFFF")
        lbl2.grid(row=2, column=2, padx=10, pady=10, sticky="e")


        self._create_image_buttons(control_panel)
       
    def _create_image_buttons(self, parent):
        """创建水平排列的图片按钮组"""
        configs = [
            {
                'size': 60,
                'normal_img': "exit.jpg",
                'command': self.exit,
                
                
            },
            {
                'size': 180,
                'normal_img': "cam.jpg",
                'command': self.capture_image,
            },
            {
                'size': 100,
                'normal_img': "read.jpg",
                'command': self.read,
            }
        ]
        i=0
        # 使用grid布局管理器
        for col, cfg in enumerate(configs):
            # 调整图片大小
            if not os.path.exists(cfg['normal_img']):
                cfg['normal_img'] = "default.png"  # 默认图片
            btn = ImageButton(parent, **cfg)
            btn.canvas.configure(borderwidth=0,relief=tk.FLAT)
            if i==0:
                btn.canvas.grid(row=0, column=2, padx=10, pady=10,sticky="ew")
            else:
                btn.canvas.grid(row=1, column=col, padx=10, pady=10, sticky="ew")
            i=i+1

    def start_capture(self):
        """启动摄像头预览"""
        if self.cap and not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.thread.start()
            self.root.after(20, self.update_frame)

    def exit(self):
        """关闭主窗口并释放资源"""
        # 停止摄像头预览相关操作
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)  # 等待线程结束（设置超时防止卡死）
        
        # 释放摄像头资源
        if self.cap:
            self.cap.release()
            self.cap = None
        
        # 清空视频显示
        self.video_frame.configure(image='')
        
        # 销毁主窗口
        self.root.destroy()  # 如果是类方法，需传入父窗口引用
        # 清理SPI资源
        data_transfer.cleanup()
        
        # 销毁主窗口
        self.root.destroy()
        
        # 关闭所有LED
        data_transfer.set_gesture_command("close")

    def show_status(self, message):
        """显示临时状态信息"""
        global name
        name = self.gesture_recognizion()
        
        if name in GESTURE_COLORS:
            message = f"识别到手势: {gesture_name}"
            # 发送手势命令到C程序
            self.send_gesture_command(name)
        else:
            message = "未识别到手势或手势无效"
        
        self.status_label.config(text=message, anchor="center", justify="center")

    def _capture_loop(self):
        """独立帧捕获线程"""
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                if self.frame_queue.full():
                    self.frame_queue.get()  # 丢弃旧帧
                self.frame_queue.put(frame)

    def update_frame(self):
        """更新画面"""
        if not self.running:
            return
        try:
            frame = self.frame_queue.get_nowait()
            # 图像处理
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame)
            imgtk = ImageTk.PhotoImage(image=img)
            self.root.after(0, self._update_gui, imgtk)
        except queue.Empty:
            pass
        finally:
            self.root.after(20, self.update_frame)
            

    def _update_gui(self, imgtk):
        """安全更新 GUI"""
        self.video_frame.imgtk = imgtk
        self.video_frame.configure(image=imgtk)

    def capture_image(self):
        """截取当前画面"""
        if self.cap and self.running:
            ret, frame = self.cap.read()
            if ret:
                target_width = 480
                target_height = 640
                frame = cv2.resize(frame, (target_width, target_height), 
                                     interpolation=cv2.INTER_AREA)
                cv2.imwrite("captured_frame.jpg", frame)
                print("截图已保存")
                self.root.after(0, lambda: self.show_status("截图已保存"))

    def _auto_capture_loop(self):
        """自动拍照循环"""
        if self.running:
            self.capture_image()
            self.root.after(4000, self._auto_capture_loop)  # 保持循环

    
    def show_status(self, message):
        """显示临时状态信息"""
        # 清空旧状态
        global name
        name=self.gesture_recognizion()
        if name=="未检测到手势":
            message=name
        else:
            message=message+f"你的手势数字为{name}"
        self.status_label.config(text=message,anchor="center",justify="center")
        # # 2秒后自动清除状态
        # self.root.after(2000, lambda: self.status_label.config(text=""))
    def read(self):
        global name, gesture_name
        name="4"
        data_transfer.set_gesture_command(name)
        return name


    def show_status(self, message):
        """显示临时状态信息"""
        global name
        name = self.gesture_recognizion()
        if name == "未检测到手势":
            message = name
        else:
            message = message + f"你的手势为: {gesture_name}"
            # 发送手势命令到C程序
            self.send_gesture_command(name)
        self.status_label.config(text=message, anchor="center", justify="center")
    
    def send_gesture_command(self, gesture_name):
        """发送手势命令到C程序"""
        try:
            # 调用C函数
            data_transfer.set_gesture_command(gesture_name)
            print(f"已发送手势命令: {gesture_name}")
        except Exception as e:
            print(f"发送手势命令失败: {str(e)}")
    
    def gesture_recognizion(self):
        
        global model, name, gesture_name
        name = "未识别"  # 默认值
        
        try:
            # 确保有权限写入
            os.makedirs("runs/detect", exist_ok=True)
            os.chmod("runs/detect", 0o777)
            
            results = model(r'captured_frame.jpg', show=True, save=True, project="runs/detect", name='predict')
            
            for result in results:
                boxes = result.boxes  # 检测框
                for box in boxes:
                    cls_id = int(box.cls[0])               # 类别索引
                    gesture_name = model.names[cls_id]     # 类别名称
                    name = gesture_name
                    print(f"识别到手势: {name}")
        except Exception as e:
            print(f"手势识别失败: {str(e)}")
        
        return name

if __name__ == "__main__":
    root = tk.Tk()
    app = CameraApp(root)
    root.protocol("WM_DELETE_WINDOW", app.exit)
    root.mainloop()