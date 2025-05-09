import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import time
from scraper import WordPressProductScraper

class ScraperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("WordPress商品采集工具 - 增强版")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        self.scraper = WordPressProductScraper()
        self.setup_ui()
        
        # 用于控制线程的变量
        self.running = False
        
    def setup_ui(self):
        # 创建标签框架
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 主页面
        main_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(main_frame, text="采集")
        
        # 设置页面
        settings_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(settings_frame, text="设置")
        
        # 日志页面
        log_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(log_frame, text="日志")
        
        # 创建主页面内容
        self.setup_main_frame(main_frame)
        
        # 创建设置页面内容
        self.setup_settings_frame(settings_frame)
        
        # 创建日志页面内容
        self.setup_log_frame(log_frame)
        
        # 状态栏
        self.status_var = tk.StringVar()
        self.status_var.set("就绪")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
    def setup_main_frame(self, parent):
        # URL输入
        url_frame = ttk.Frame(parent)
        url_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(url_frame, text="网站URL:").pack(side=tk.LEFT)
        self.url_entry = ttk.Entry(url_frame, width=50)
        self.url_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # 采集按钮
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, pady=5)
        
        self.single_btn = ttk.Button(btn_frame, text="采集单个商品", command=self.scrape_single)
        self.single_btn.pack(side=tk.LEFT, padx=5)
        
        self.page_btn = ttk.Button(btn_frame, text="采集整页商品", command=self.scrape_page)
        self.page_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(btn_frame, text="停止采集", command=self.stop_scraping, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text="清空结果", command=self.clear_results).pack(side=tk.LEFT, padx=5)
        
        # 导出按钮
        export_frame = ttk.Frame(parent)
        export_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(export_frame, text="导出为CSV", command=lambda: self.export_data("csv")).pack(side=tk.LEFT, padx=5)
        ttk.Button(export_frame, text="导出为TXT", command=lambda: self.export_data("txt")).pack(side=tk.LEFT, padx=5)
        ttk.Button(export_frame, text="导出为JSON", command=lambda: self.export_data("json")).pack(side=tk.LEFT, padx=5)
        ttk.Button(export_frame, text="导出为WooCommerce", command=lambda: self.export_data("woocommerce")).pack(side=tk.LEFT, padx=5)
        ttk.Button(export_frame, text="WooCommerce分批导出", command=self.export_batch_woocommerce).pack(side=tk.LEFT, padx=5)
        
        # 进度框架
        progress_frame = ttk.LabelFrame(parent, text="进度")
        progress_frame.pack(fill=tk.X, pady=5)
        
        # 详细进度信息
        self.progress_var = tk.StringVar()
        self.progress_var.set("0/0")
        ttk.Label(progress_frame, textvariable=self.progress_var).pack(side=tk.TOP, fill=tk.X)
        
        # 进度条
        self.progress = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, length=100, mode='determinate')
        self.progress.pack(fill=tk.X, pady=5)
        
        # 结果显示
        result_frame = ttk.LabelFrame(parent, text="采集结果")
        result_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 创建滚动条
        scrollbar = ttk.Scrollbar(result_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 创建文本框
        self.result_text = scrolledtext.ScrolledText(result_frame, yscrollcommand=scrollbar.set)
        self.result_text.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.result_text.yview)
        
    def setup_settings_frame(self, parent):
        # 代理设置
        proxy_frame = ttk.LabelFrame(parent, text="代理设置")
        proxy_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(proxy_frame, text="代理地址:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.proxy_entry = ttk.Entry(proxy_frame, width=40)
        self.proxy_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W+tk.E)
        ttk.Label(proxy_frame, text="格式: http://ip:port").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        
        ttk.Button(proxy_frame, text="应用代理", command=self.apply_proxy).grid(row=1, column=0, padx=5, pady=5)
        ttk.Button(proxy_frame, text="清除代理", command=self.clear_proxy).grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        
        # 请求间隔设置
        interval_frame = ttk.LabelFrame(parent, text="请求间隔设置 (秒)")
        interval_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(interval_frame, text="最小间隔:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.min_interval = ttk.Spinbox(interval_frame, from_=0.5, to=10, increment=0.5, width=5)
        self.min_interval.set("1")
        self.min_interval.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(interval_frame, text="最大间隔:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.max_interval = ttk.Spinbox(interval_frame, from_=0.5, to=20, increment=0.5, width=5)
        self.max_interval.set("3")
        self.max_interval.grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)
        
        ttk.Button(interval_frame, text="应用间隔", command=self.apply_interval).grid(row=1, column=0, padx=5, pady=5, columnspan=2)
        
        # 图片设置
        image_frame = ttk.LabelFrame(parent, text="图片设置")
        image_frame.pack(fill=tk.X, pady=5)
        
        self.download_images_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(image_frame, text="下载图片", variable=self.download_images_var, command=self.toggle_image_download).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(image_frame, text="图片保存路径:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.image_folder_entry = ttk.Entry(image_frame, width=40)
        self.image_folder_entry.insert(0, self.scraper.image_folder)
        self.image_folder_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W+tk.E)
        
        ttk.Button(image_frame, text="浏览", command=self.browse_image_folder).grid(row=1, column=2, padx=5, pady=5)
        ttk.Button(image_frame, text="应用", command=self.apply_image_settings).grid(row=2, column=0, padx=5, pady=5)
        
        # 网站自动检测设置
        website_frame = ttk.LabelFrame(parent, text="网站适配设置")
        website_frame.pack(fill=tk.X, pady=5)
        
        self.auto_detect_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(website_frame, text="启用网站自动检测", variable=self.auto_detect_var).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        
        # 调试模式设置
        self.debug_mode_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(website_frame, text="启用调试模式", variable=self.debug_mode_var, command=self.toggle_debug_mode).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(website_frame, text="支持的网站:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        supported_sites = list(self.scraper.site_specific_selectors.keys())
        supported_sites_text = ", ".join(supported_sites)
        ttk.Label(website_frame, text=supported_sites_text).grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        
        # 高级抓取设置
        advanced_frame = ttk.LabelFrame(parent, text="高级抓取设置")
        advanced_frame.pack(fill=tk.X, pady=5)
        
        self.max_retries_var = tk.IntVar(value=self.scraper.max_retries)
        ttk.Label(advanced_frame, text="最大重试次数:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.max_retries_entry = ttk.Spinbox(advanced_frame, from_=1, to=10, textvariable=self.max_retries_var, width=5)
        self.max_retries_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        self.timeout_var = tk.IntVar(value=10)
        ttk.Label(advanced_frame, text="请求超时(秒):").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.timeout_entry = ttk.Spinbox(advanced_frame, from_=5, to=60, textvariable=self.timeout_var, width=5)
        self.timeout_entry.grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)
        
        ttk.Button(advanced_frame, text="应用高级设置", command=self.apply_advanced_settings).grid(row=1, column=0, padx=5, pady=5, columnspan=2)
        
        # 自定义选择器设置
        selector_frame = ttk.LabelFrame(parent, text="自定义选择器 (CSS选择器)")
        selector_frame.pack(fill=tk.X, pady=5, expand=True)
        
        # 创建选择器输入框
        row = 0
        self.selector_entries = {}
        
        for key, value in self.scraper.selectors.items():
            ttk.Label(selector_frame, text=f"{key}:").grid(row=row, column=0, padx=5, pady=2, sticky=tk.W)
            entry = ttk.Entry(selector_frame, width=40)
            entry.insert(0, value)
            entry.grid(row=row, column=1, padx=5, pady=2, sticky=tk.W+tk.E)
            self.selector_entries[key] = entry
            row += 1
        
        ttk.Button(selector_frame, text="应用选择器", command=self.apply_selectors).grid(row=row, column=0, padx=5, pady=5)
        ttk.Button(selector_frame, text="重置默认值", command=self.reset_selectors).grid(row=row, column=1, padx=5, pady=5, sticky=tk.W)
        
    def setup_log_frame(self, parent):
        # 创建日志显示区域
        log_frame = ttk.Frame(parent)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建滚动条
        scrollbar = ttk.Scrollbar(log_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 创建文本框
        self.log_text = scrolledtext.ScrolledText(log_frame, yscrollcommand=scrollbar.set)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.log_text.yview)
        
        # 清空按钮
        ttk.Button(parent, text="清空日志", command=self.clear_log).pack(pady=5)
        
    def log_message(self, message):
        """将消息添加到日志"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)  # 滚动到最新消息
        
    def status_callback(self, message):
        """状态回调函数，用于接收爬虫状态更新"""
        # 更新状态栏
        self.status_var.set(message)
        
        # 添加到日志
        self.log_message(message)
        
        # 更新GUI（必须在主线程中执行）
        self.root.update_idletasks()
        
    def progress_callback(self, current, total):
        """进度回调函数，用于更新进度条"""
        # 更新进度文本
        self.progress_var.set(f"{current+1}/{total}")
        
        # 更新进度条
        progress_value = int((current + 1) / total * 100)
        self.progress['value'] = progress_value
        
        # 更新GUI
        self.root.update_idletasks()
        
    def apply_proxy(self):
        """应用代理设置"""
        proxy = self.proxy_entry.get().strip()
        if proxy:
            if self.scraper.set_proxy(proxy):
                self.status_callback(f"已设置代理: {proxy}")
            else:
                messagebox.showerror("错误", "无法设置代理，格式可能不正确")
        else:
            messagebox.showinfo("提示", "请输入代理地址")
            
    def clear_proxy(self):
        """清除代理设置"""
        self.proxy_entry.delete(0, tk.END)
        self.scraper.set_proxy(None)
        self.status_callback("已清除代理设置")
        
    def apply_interval(self):
        """应用请求间隔设置"""
        try:
            min_interval = float(self.min_interval.get())
            max_interval = float(self.max_interval.get())
            
            if self.scraper.set_request_interval(min_interval, max_interval):
                self.status_callback(f"已设置请求间隔: {min_interval}~{max_interval}秒")
            else:
                messagebox.showerror("错误", "无法设置请求间隔，请确保最小值小于等于最大值且均为正数")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")
            
    def apply_selectors(self):
        """应用自定义选择器设置"""
        selectors_dict = {}
        for key, entry in self.selector_entries.items():
            selectors_dict[key] = entry.get().strip()
            
        if self.scraper.set_selectors(selectors_dict):
            self.status_callback("已应用自定义选择器")
        else:
            messagebox.showerror("错误", "无法应用选择器设置")
            
    def reset_selectors(self):
        """重置选择器为默认值"""
        default_selectors = {
            'name': '.product_title',
            'price': '.price .amount',
            'description': '.woocommerce-product-details__short-description',
            'image': '.woocommerce-product-gallery__image img',
            'categories': '.posted_in a',
            'tags': '.tagged_as a',
            'sku': '.sku',
            'product_links': '.products .product a.woocommerce-LoopProduct-link'
        }
        
        for key, value in default_selectors.items():
            if key in self.selector_entries:
                self.selector_entries[key].delete(0, tk.END)
                self.selector_entries[key].insert(0, value)
                
        self.scraper.set_selectors(default_selectors)
        self.status_callback("已重置选择器为默认值")
        
    def stop_scraping(self):
        """停止正在进行的采集任务"""
        self.running = False
        self.status_callback("正在停止采集...")
        
    def toggle_ui_state(self, is_running):
        """切换UI状态（运行中/空闲）"""
        state = tk.DISABLED if is_running else tk.NORMAL
        opposite_state = tk.NORMAL if is_running else tk.DISABLED
        
        # 更新按钮状态
        self.single_btn['state'] = state
        self.page_btn['state'] = state
        self.stop_btn['state'] = opposite_state
        
        # 更新运行状态
        self.running = is_running
        
    def clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, tk.END)
        self.scraper.clear_error_log()
        self.status_callback("已清空日志")
        
    def toggle_debug_mode(self):
        """切换调试模式"""
        debug_enabled = self.debug_mode_var.get()
        self.scraper.set_debug_mode(debug_enabled)
        if debug_enabled:
            self.status_callback("已启用调试模式，将保存网页内容到debug_page.html")
        else:
            self.status_callback("已关闭调试模式")
        
    def scrape_single(self):
        """采集单个商品"""
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("错误", "请输入商品URL")
            return
            
        self.status_callback("正在采集单个商品...")
        self.toggle_ui_state(True)
        self.progress['value'] = 0
        self.running = True
        
        def task():
            # 如果启用了自动检测，则检测网站适配
            if self.auto_detect_var.get():
                detected = self.scraper.auto_detect_selectors(url)
                if detected:
                    self.status_callback("已自动适配网站选择器")
                else:
                    self.status_callback("使用默认选择器")
            
            # 特殊处理bkhorsebag网站
            if 'bkhorsebag' in url:
                self.status_callback("检测到bkhorsebag网站，使用特殊处理方式")
                
            product = self.scraper.scrape_single_product(url, self.status_callback)
            
            # 在主线程中更新UI
            self.root.after(0, lambda: self.update_ui(product))
            
        threading.Thread(target=task, daemon=True).start()
        
    def scrape_page(self):
        """采集整页商品"""
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("错误", "请输入页面URL")
            return
            
        self.status_callback("正在采集页面商品...")
        self.toggle_ui_state(True)
        self.progress['value'] = 0
        self.running = True
        
        def task():
            # 如果启用了自动检测，则检测网站适配
            if self.auto_detect_var.get():
                detected = self.scraper.auto_detect_selectors(url)
                if detected:
                    self.status_callback("已自动适配网站选择器")
                else:
                    self.status_callback("使用默认选择器")
                    
            count = self.scraper.scrape_page_products(
                url, 
                self.status_callback, 
                self.progress_callback
            )
            
            # 在主线程中更新UI
            self.root.after(0, lambda: self.update_ui_page(count))
            
        threading.Thread(target=task, daemon=True).start()
        
    def update_ui(self, product):
        """更新UI（单个商品）"""
        self.toggle_ui_state(False)
        self.progress['value'] = 100
        
        if product:
            self.result_text.insert(tk.END, f"商品名称: {product['name']}\n")
            self.result_text.insert(tk.END, f"商品价格: {product['price']}\n")
            self.result_text.insert(tk.END, f"商品SKU: {product.get('sku', '')}\n")
            self.result_text.insert(tk.END, f"商品分类: {product.get('categories', '')}\n")
            self.result_text.insert(tk.END, f"商品图片: {product.get('image', '')}\n")
            self.result_text.insert(tk.END, f"采集时间: {product.get('scrape_time', '')}\n")
            self.result_text.insert(tk.END, "-" * 50 + "\n\n")
            self.status_var.set(f"成功采集1个商品")
            self.result_text.see(tk.END)
        else:
            self.status_var.set("采集失败")
            error_log = self.scraper.get_error_log()
            if error_log:
                messagebox.showerror("错误", error_log[-1])
            else:
                messagebox.showerror("错误", "采集商品失败，请检查URL是否正确")
            
    def update_ui_page(self, count):
        """更新UI（整页商品）"""
        self.toggle_ui_state(False)
        
        if count > 0:
            self.result_text.insert(tk.END, f"成功采集{count}个商品\n\n")
            for product in self.scraper.products[-count:]:
                self.result_text.insert(tk.END, f"商品名称: {product['name']}\n")
                self.result_text.insert(tk.END, f"商品价格: {product['price']}\n")
                self.result_text.insert(tk.END, f"商品SKU: {product.get('sku', '')}\n")
                self.result_text.insert(tk.END, "-" * 50 + "\n\n")
            self.status_var.set(f"成功采集{count}个商品")
            self.result_text.see(tk.END)
        else:
            self.status_var.set("采集失败")
            error_log = self.scraper.get_error_log()
            if error_log:
                messagebox.showerror("错误", error_log[-1])
            else:
                messagebox.showerror("错误", "采集商品失败，请检查URL是否正确")
            
    def export_data(self, file_type):
        """导出数据到文件"""
        if not self.scraper.products:
            messagebox.showinfo("提示", "没有数据可导出")
            return
            
        try:
            file_types = {
                "csv": ("CSV 文件", "*.csv"),
                "txt": ("文本文件", "*.txt"),
                "json": ("JSON 文件", "*.json"),
                "woocommerce": ("WooCommerce CSV 文件", "*.csv")
            }
            
            # 获取保存路径
            file_path = filedialog.asksaveasfilename(
                title=f"保存为{file_type.upper()}",
                filetypes=[(file_types[file_type][0], file_types[file_type][1])]
            )
            
            if not file_path:
                return
            
            # 确保有正确的扩展名
            if not file_path.endswith(f".{file_types[file_type][1].split('.')[-1]}"):
                file_path += f".{file_types[file_type][1].split('.')[-1]}"
            
            # 导出文件
            if file_type == "csv":
                success = self.scraper.export_to_csv(file_path)
            elif file_type == "txt":
                success = self.scraper.export_to_txt(file_path)
            elif file_type == "json":
                success = self.scraper.export_to_json(file_path)
            elif file_type == "woocommerce":
                success = self.scraper.export_to_woocommerce_csv(file_path)
            
            if success:
                self.status_callback(f"已成功导出到 {file_path}")
                messagebox.showinfo("成功", f"数据已成功导出到 {file_path}")
            else:
                error_logs = "\n".join(self.scraper.error_log[-3:])
                messagebox.showerror("导出失败", f"导出失败，请检查文件路径是否有效\n最近错误:\n{error_logs}")
            
        except Exception as e:
            messagebox.showerror("导出错误", f"导出时发生错误: {str(e)}")
        
    def toggle_image_download(self):
        """切换图片下载设置"""
        enabled = self.download_images_var.get()
        self.scraper.set_download_images(enabled)
        status = "启用" if enabled else "禁用"
        self.status_callback(f"图片下载已{status}")
        
    def browse_image_folder(self):
        """浏览并选择图片保存文件夹"""
        folder_path = filedialog.askdirectory(title="选择图片保存文件夹")
        if folder_path:
            self.image_folder_entry.delete(0, tk.END)
            self.image_folder_entry.insert(0, folder_path)
            
    def apply_image_settings(self):
        """应用图片设置"""
        folder_path = self.image_folder_entry.get().strip()
        if folder_path:
            self.scraper.set_image_folder(folder_path)
            self.status_callback(f"图片保存路径已设置为: {folder_path}")
        else:
            messagebox.showinfo("提示", "请输入有效的图片保存路径")
        
    def clear_results(self):
        """清空结果"""
        self.scraper.clear_products()
        self.result_text.delete(1.0, tk.END)
        self.status_var.set("已清空结果")
        self.progress['value'] = 0

    def apply_advanced_settings(self):
        """应用高级抓取设置"""
        try:
            max_retries = self.max_retries_var.get()
            timeout = self.timeout_var.get()
            
            self.scraper.max_retries = max_retries
            self.scraper.timeout = timeout
            
            self.status_callback(f"已应用高级设置: 最大重试次数={max_retries}, 超时时间={timeout}秒")
        except Exception as e:
            messagebox.showerror("错误", f"应用高级设置失败: {str(e)}")

    def export_batch_woocommerce(self):
        """分批导出为WooCommerce可导入的CSV文件"""
        if not self.scraper.products:
            messagebox.showinfo("提示", "没有数据可导出")
            return
        
        try:
            # 获取每批大小
            batch_size_dialog = tk.Toplevel(self.root)
            batch_size_dialog.title("设置批次大小")
            batch_size_dialog.geometry("300x150")
            batch_size_dialog.resizable(False, False)
            batch_size_dialog.grab_set()  # 模态对话框
            
            ttk.Label(batch_size_dialog, text="每个文件包含的商品数量:").pack(pady=(20, 5))
            
            batch_size_var = tk.IntVar(value=5)
            batch_size_spinner = ttk.Spinbox(batch_size_dialog, from_=1, to=50, textvariable=batch_size_var, width=10)
            batch_size_spinner.pack(pady=5)
            
            def start_export():
                batch_size = batch_size_var.get()
                batch_size_dialog.destroy()
                
                # 选择保存文件夹
                folder_path = filedialog.askdirectory(title="选择保存分批文件的文件夹")
                if not folder_path:
                    return
                    
                # 执行导出
                result = self.scraper.split_and_export_for_woocommerce(folder_path, batch_size)
                
                if result:
                    self.status_callback(f"已成功导出{len(result)}个文件到 {folder_path}")
                    messagebox.showinfo("成功", f"数据已成功分批导出到 {folder_path}\n共{len(result)}个文件，请参阅导入说明.txt")
                else:
                    error_logs = "\n".join(self.scraper.error_log[-3:])
                    messagebox.showerror("导出失败", f"分批导出失败\n最近错误:\n{error_logs}")
            
            ttk.Button(batch_size_dialog, text="确定", command=start_export).pack(pady=10)
            
        except Exception as e:
            messagebox.showerror("导出错误", f"分批导出时发生错误: {str(e)}")