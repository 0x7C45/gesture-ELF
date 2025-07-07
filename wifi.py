import sys
import subprocess
import platform
import re
import time
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QLineEdit, 
                            QPushButton, QVBoxLayout, QHBoxLayout, QComboBox,
                            QTextEdit, QProgressBar)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer

class WifiScanner(QThread):
    """WiFi扫描线程类"""
    scan_signal = pyqtSignal(list)  # 扫描结果信号
    error_signal = pyqtSignal(str)  # 错误信号

    def run(self):
        try:
            if platform.system() == "Windows":
                cmd = 'netsh wlan show networks mode=bssid'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                networks = self._parse_windows_output(result.stdout)
            else:
                cmd = 'nmcli dev wifi'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                networks = self._parse_linux_output(result.stdout)
                
            if networks:
                self.scan_signal.emit(networks)
            else:
                self.error_signal.emit("未检测到可用网络")
        except Exception as e:
            self.error_signal.emit(str(e))

    def _parse_windows_output(self, output):
        """解析Windows扫描结果"""
        networks = []
        lines = output.split('\n')
        for i, line in enumerate(lines):
            if "SSID" in line:
                ssid = line.split(':')[1].strip()
                # 查找信号强度
                signal_line = lines[i+4] if i+4 < len(lines) else ""
                signal = re.search(r'\d+%', signal_line)
                signal = signal.group(0) if signal else "未知"
                networks.append((ssid, signal))
        return networks

    def _parse_linux_output(self, output):
        """解析Linux扫描结果"""
        networks = []
        lines = output.split('\n')[1:]  # 跳过标题行
        for line in lines:
            if line.strip():
                parts = re.split(r'\s{2,}', line.strip())
                ssid = parts[1]
                signal = parts[6] if len(parts) > 6 else "未知"
                networks.append((ssid, signal))
        return networks

class ConnectionThread(QThread):
    """连接操作线程类"""
    status_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)

    def __init__(self, ssid, password):
        super().__init__()
        self.ssid = ssid
        self.password = password
        self.is_running = True

    def run(self):
        try:
            if platform.system() == "Windows":
                cmd = f'netsh wlan connect name="{self.ssid}" ssid="{self.ssid}" key="{self.password}"'
            else:
                cmd = f'nmcli dev wifi connect "{self.ssid}" password="{self.password}"'
            
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            total = 100
            for i in range(total):
                if not self.is_running:
                    break
                self.progress_signal.emit(i+1)
                time.sleep(0.05)
            
            stdout, stderr = process.communicate()
            if process.returncode == 0:
                self.status_signal.emit(f"成功连接到 {self.ssid}")
            else:
                self.status_signal.emit(f"连接失败: {stderr.decode()}")
        except Exception as e:
            self.status_signal.emit(f"错误: {str(e)}")
        finally:
            self.is_running = False

    def stop(self):
        self.is_running = False
        self.terminate()

class WifiManager(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.current_thread = None
        self.network_timer = self.startTimer(5000)
        self.scan_thread = WifiScanner()
        self.scan_thread.scan_signal.connect(self.update_wifi_list)
        self.scan_thread.error_signal.connect(self.show_error)
    def timerEvent(self, event):
        """定时检测网络状态"""
        if platform.system() == "Windows":
            cmd = "ping -n 1 www.baidu.com"
        else:
            cmd = "ping -c 1 www.baidu.com"
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if "TTL=" in result.stdout:
            self.status_bar.setText("网络已连接")
            self.status_bar.setStyleSheet("color: green")
        else:
            self.status_bar.setText("网络未连接")
            self.status_bar.setStyleSheet("color: red")
    def init_ui(self):
        # 主布局
        main_layout = QVBoxLayout()
        
        # 状态显示区
        self.status_bar = QLabel("就绪")
        self.status_bar.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_bar)

        # 扫描控制区
        scan_layout = QHBoxLayout()
        self.scan_btn = QPushButton("扫描网络")
        self.scan_btn.clicked.connect(self.start_scan)
        scan_layout.addWidget(self.scan_btn)
        main_layout.addLayout(scan_layout)

        # 网络选择区
        self.wifi_combo = QComboBox()
        self.wifi_combo.setFixedHeight(30)
        main_layout.addWidget(self.wifi_combo)

        # 连接配置区
        config_layout = QVBoxLayout()
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("密码")
        self.password_input.setEchoMode(QLineEdit.Password)
        config_layout.addWidget(self.password_input)

        self.connect_btn = QPushButton("连接")
        self.connect_btn.clicked.connect(self.start_connection)
        config_layout.addWidget(self.connect_btn)
        main_layout.addLayout(config_layout)

        # 日志显示区
        self.log_browser = QTextEdit()
        self.log_browser.setReadOnly(True)
        self.log_browser.setFixedHeight(150)
        main_layout.addWidget(self.log_browser)

        self.setLayout(main_layout)
        self.setWindowTitle("WiFi 管理器")
        self.setFixedSize(400, 400)

    def start_scan(self):
        """启动扫描线程"""
        if self.scan_thread.isRunning():
            return
        self.scan_btn.setEnabled(False)
        self.scan_thread.start()
        self.log_browser.append("正在扫描可用网络...")

    def update_wifi_list(self, networks):
        """更新WiFi列表"""
        self.wifi_combo.clear()
        for ssid, signal in networks:
            self.wifi_combo.addItem(f"{ssid} ({signal})")
        self.log_browser.append("扫描完成")

    def start_connection(self):
        """启动连接流程"""
        ssid = self.wifi_combo.currentText().split(' ')[0]
        password = self.password_input.text().strip()

        if not ssid or not password:
            self.log_browser.append("请选择网络并输入密码")
            return

        if self.current_thread and self.current_thread.is_running:
            self.log_browser.append("已有连接任务在进行中")
            return

        self.log_browser.append(f"正在连接 {ssid}...")
        self.connect_btn.setEnabled(False)
        self.current_thread = ConnectionThread(ssid, password)
        
        self.current_thread.progress_signal.connect(self.update_progress)
        self.current_thread.status_signal.connect(self.connection_result)
        self.current_thread.start()

    def update_progress(self, value):
        """更新连接进度条（模拟）"""
        self.status_bar.setText(f"连接进度: {value}%")
        if value == 100:
            self.status_bar.setText("连接完成")

    def connection_result(self, message):
        """处理连接结果"""
        self.log_browser.append(message)
        self.connect_btn.setEnabled(True)
        self.current_thread = None

    def show_error(self, message):
        """显示错误信息"""
        self.log_browser.append(f"错误: {message}")
        self.scan_btn.setEnabled(True)

    def closeEvent(self, event):
        """关闭事件处理"""
        if self.current_thread and self.current_thread.is_running:
            self.current_thread.stop()
            self.current_thread.wait()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = WifiManager()
    ex.show()
    sys.exit(app.exec_())