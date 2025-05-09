import requests
from bs4 import BeautifulSoup
import csv
import json
import os
import time
import threading
import random
from urllib.parse import urlparse, urljoin
import re
import shutil
from pathlib import Path
import hashlib
import urllib.parse

class WordPressProductScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
        self.products = []
        self.proxies = None
        self.request_interval = (1, 3)  # 默认请求间隔1-3秒
        self.max_retries = 3  # 最大重试次数
        self.error_log = []  # 错误日志
        self.timeout = 10  # 请求超时时间(秒)
        self.debug_mode = False  # 调试模式
        self.download_images = True  # 默认下载图片
        self.downloaded_images = {}  # 存储下载的图片路径
        self.image_folder = "product_images"  # 图片保存文件夹
        
        # 创建图片目录
        if not os.path.exists(self.image_folder):
            os.makedirs(self.image_folder)
        
        # 默认选择器配置
        self.selectors = {
            'name': '.product_title',
            'price': '.price .amount',
            'description': '.woocommerce-product-details__short-description',
            'image': '.woocommerce-product-gallery__image img',
            'categories': '.posted_in a',
            'tags': '.tagged_as a',
            'sku': '.sku',
            'product_links': '.products .product a.woocommerce-LoopProduct-link'
        }
        
        # 网站特定选择器配置
        self.site_specific_selectors = {
            'bkhorsebag.com': {
                'name': 'h1, .product-title, title',  # 标题可能在多个位置
                'price': '.price, .product-price, [itemprop="price"]',  # 多个可能的价格选择器
                'description': '.product-description, .product-info, .description',
                'image': '.product-image img, img.main-image, .gallery img',
                'categories': '.breadcrumb a, .categories a, .product-categories a',
                'tags': '.tags a, .product-tags a',
                'sku': '.sku, .product-sku, [itemprop="sku"]',
                'product_links': 'a[href*="product"], a[href*="item"], .product-list a'
            },
            'shopify': {
                'name': '.product-title, .product__title, h1.title, h1',
                'price': '.product-price, .price, .product__price',
                'description': '.product-description, .description, .product__description',
                'image': '.product-image img, .product__image img, .featured-image',
                'categories': '.product-categories a, .breadcrumb a',
                'tags': '.product-tags a, .tags a',
                'sku': '.sku, .product-sku, [data-product-sku]',
                'product_links': '.product-item a, .product-card a, .grid-product__link'
            },
            'woocommerce': {
                'name': '.product_title, h1.entry-title',
                'price': '.price, .woocommerce-Price-amount',
                'description': '.woocommerce-product-details__short-description, .summary p',
                'image': '.woocommerce-product-gallery__image img, .wp-post-image',
                'categories': '.posted_in a',
                'tags': '.tagged_as a',
                'sku': '.sku',
                'product_links': '.products .product a.woocommerce-LoopProduct-link, .products .product a:first-child'
            },
            'magento': {
                'name': '.page-title, h1',
                'price': '.price, .product-info-price .price',
                'description': '.product-info-main .description, .product.attribute.description',
                'image': '.gallery-placeholder img, .fotorama__img',
                'categories': '.breadcrumbs a',
                'tags': '.product-tags a',
                'sku': '.sku .value, [itemprop="sku"]',
                'product_links': '.product-item a.product-item-link, .product-items a.product-item-photo'
            },
            'prestashop': {
                'name': '.product-name, .h1, h1[itemprop="name"]',
                'price': '.product-price, [itemprop="price"]',
                'description': '.product-description, [itemprop="description"]',
                'image': '.product-cover img, #product-images-large img',
                'categories': '.breadcrumb a',
                'tags': '.product-tags a',
                'sku': '.product-reference span, [itemprop="sku"]',
                'product_links': '.product-miniature a.thumbnail, .js-product-miniature a.product-thumbnail'
            }
        }
        
        # 添加LOGO和非产品图片过滤规则
        self.logo_filter = {
            'url_keywords': ['logo', 'icon', 'favicon', 'header', 'footer', 'banner', 'background', 'btn', 'button'],
            'class_keywords': ['logo', 'icon', 'header', 'footer', 'banner', 'nav', 'menu', 'sidebar', 'social'],
            'size_threshold': 50,  # 图片尺寸小于这个阈值(像素)可能是LOGO
            'id_keywords': ['logo', 'site-logo', 'header-logo', 'footer-logo', 'brand-logo']
        }
        
    def set_debug_mode(self, enabled=True):
        """设置调试模式"""
        self.debug_mode = enabled
        return True
        
    def set_proxy(self, proxy=None):
        """设置代理"""
        if proxy:
            self.proxies = {
                'http': proxy,
                'https': proxy
            }
        else:
            self.proxies = None
        return True
        
    def set_request_interval(self, min_interval, max_interval):
        """设置请求间隔时间"""
        if min_interval > 0 and max_interval >= min_interval:
            self.request_interval = (min_interval, max_interval)
            return True
        return False
        
    def set_selectors(self, selectors_dict):
        """设置自定义选择器"""
        for key, value in selectors_dict.items():
            if key in self.selectors and value.strip():
                self.selectors[key] = value.strip()
        return True

    def auto_detect_selectors(self, url):
        """根据URL自动检测适用的选择器"""
        domain = urlparse(url).netloc
        
        # 移除www.前缀
        if domain.startswith('www.'):
            domain = domain[4:]
            
        # 1. 直接匹配特定域名
        for site_domain, selectors in self.site_specific_selectors.items():
            if site_domain in domain:
                self.selectors = selectors.copy()
                return True
        
        # 特殊处理bkhorsebag.com
        if 'bkhorsebag' in domain:
            self.selectors = self.site_specific_selectors['bkhorsebag.com'].copy()
            return True
                
        # 2. 通用平台检测
        # 检查是否为Shopify商店
        if '/products/' in url or domain.endswith('myshopify.com'):
            self.selectors = self.site_specific_selectors['shopify'].copy()
            return True
            
        # 检查是否为WooCommerce商店
        if '/product/' in url or '/shop/' in url:
            # 发起一个请求来检查页面源代码
            try:
                response = requests.get(url, headers=self.headers, timeout=self.timeout)
                if 'woocommerce' in response.text.lower() or 'wp-content' in response.text.lower():
                    self.selectors = self.site_specific_selectors['woocommerce'].copy()
                    return True
            except:
                pass
        
        # 检查是否为Magento商店
        if '/catalog/product/view/' in url:
            self.selectors = self.site_specific_selectors['magento'].copy()
            return True
            
        # 检查是否为PrestaShop商店
        if 'id_product=' in url:
            self.selectors = self.site_specific_selectors['prestashop'].copy()
            return True
                
        # 未找到匹配的特定选择器，使用默认
        return False
        
    def get_error_log(self):
        """获取错误日志"""
        return self.error_log
        
    def clear_error_log(self):
        """清空错误日志"""
        self.error_log = []
        
    def _make_request(self, url, callback=None, timeout=10):
        """发送请求并处理重试逻辑"""
        for attempt in range(self.max_retries):
            try:
                response = requests.get(
                    url, 
                    headers=self.headers, 
                    proxies=self.proxies,
                    timeout=timeout
                )
                response.raise_for_status()  # 检查HTTP错误
                return response
            except requests.exceptions.RequestException as e:
                error_msg = f"请求失败 ({attempt+1}/{self.max_retries}): {url} - {str(e)}"
                self.error_log.append(error_msg)
                if callback:
                    callback(f"重试中... {error_msg}")
                time.sleep(2)  # 重试前等待
        
        # 所有尝试都失败
        error_msg = f"在{self.max_retries}次尝试后仍无法访问: {url}"
        self.error_log.append(error_msg)
        if callback:
            callback(error_msg)
        return None
        
    def _validate_product_data(self, product):
        """验证商品数据有效性"""
        # 确保所有字段存在
        required_fields = ['name', 'price']
        for field in required_fields:
            if not product.get(field):
                return False
                
        # 确保名称不为空
        if not product['name'].strip():
            return False
            
        return True
    
    def _extract_text_safely(self, element):
        """安全提取文本内容，处理None值"""
        if element:
            return element.text.strip()
        return ""

    def _is_logo_or_icon(self, img_tag, img_url):
        """检查图片是否为LOGO或图标"""
        # 1. 检查图片URL中是否包含标志性关键词
        img_url_lower = img_url.lower()
        for keyword in self.logo_filter['url_keywords']:
            if keyword in img_url_lower:
                return True
                
        # 2. 检查图片class属性
        if img_tag and 'class' in img_tag.attrs:
            img_classes = ' '.join(img_tag['class']).lower()
            for keyword in self.logo_filter['class_keywords']:
                if keyword in img_classes:
                    return True
        
        # 3. 检查图片id属性
        if img_tag and 'id' in img_tag.attrs:
            img_id = img_tag['id'].lower()
            for keyword in self.logo_filter['id_keywords']:
                if keyword in img_id:
                    return True
        
        # 4. 检查图片alt属性
        if img_tag and 'alt' in img_tag.attrs:
            img_alt = img_tag['alt'].lower()
            if 'logo' in img_alt or 'icon' in img_alt:
                return True
        
        # 5. 检查图片尺寸属性
        if img_tag and ('width' in img_tag.attrs or 'height' in img_tag.attrs):
            width = int(img_tag.get('width', '1000').replace('px', '')) if img_tag.get('width', '').replace('px', '').isdigit() else 1000
            height = int(img_tag.get('height', '1000').replace('px', '')) if img_tag.get('height', '').replace('px', '').isdigit() else 1000
            
            # 如果宽度或高度小于阈值，可能是LOGO或图标
            if width < self.logo_filter['size_threshold'] or height < self.logo_filter['size_threshold']:
                return True
        
        # 6. 检查图片位置，通常LOGO在header或footer中
        if img_tag:
            parents = img_tag.find_parents()
            for parent in parents:
                if parent.name and parent.get('id'):
                    parent_id = parent['id'].lower()
                    if 'header' in parent_id or 'footer' in parent_id or 'logo' in parent_id:
                        return True
                
                if parent.name and parent.get('class'):
                    parent_classes = ' '.join(parent.get('class', [])).lower()
                    if ('header' in parent_classes or 'footer' in parent_classes or 
                        'logo' in parent_classes or 'nav' in parent_classes or 
                        'menu' in parent_classes):
                        return True
        
        return False

    def _extract_product_data_bkhorsebag(self, soup, url):
        """专门处理bkhorsebag.com网站的产品数据提取"""
        product = {}
        
        # 获取基础URL用于处理相对路径
        base_url = urlparse(url)
        base_domain = f"{base_url.scheme}://{base_url.netloc}"
        
        # 尝试从标题中提取名称
        title_tag = soup.find('title')
        if title_tag and title_tag.text:
            product['name'] = title_tag.text.strip()
        else:
            # 尝试从网页内容中查找可能的产品名称
            h1_tags = soup.find_all('h1')
            if h1_tags:
                product['name'] = h1_tags[0].text.strip()
            else:
                # 最后尝试从URL中提取
                product_id = re.search(r'id=(\d+)', url)
                if product_id:
                    product['name'] = f"BK Horse Product {product_id.group(1)}"
                else:
                    product['name'] = "BK Horse Product"
        
        # 设置价格
        # 先查找常见价格标签
        price_patterns = ['.price', '[class*="price"]', '[itemprop="price"]']
        for pattern in price_patterns:
            price_elem = soup.select_one(pattern)
            if price_elem:
                product['price'] = price_elem.text.strip()
                break
        
        # 如果还没找到，尝试分析页面文本查找价格格式
        if not product.get('price'):
            # 查找价格可能的文本模式, 如: $123.45 或 ¥123
            price_texts = re.findall(r'[\$¥€£]([\d\,\.]+)', str(soup))
            if price_texts:
                product['price'] = f"${price_texts[0]}"
            else:
                # 如果仍然没有找到，给一个默认值确保数据有效
                product['price'] = "价格待定"
        
        # 提取描述
        description_patterns = ['.description', '.product-description', '.content', '.details']
        for pattern in description_patterns:
            desc_elem = soup.select_one(pattern)
            if desc_elem:
                product['description'] = str(desc_elem)
                break
        
        if not product.get('description'):
            # 使用所有段落的文本作为描述
            paragraphs = soup.find_all('p')
            if paragraphs:
                product['description'] = ' '.join([p.text.strip() for p in paragraphs[:3]])
            else:
                product['description'] = ""
        
        # 提取多张图片 - 修改为支持多图片采集
        product['images'] = []  # 存储多张图片
        
        # 尝试查找所有可能的产品图片
        image_patterns = [
            'img[src*="product"]', 
            '.gallery img', 
            '.product img', 
            'img.main-image', 
            '.product-image img',
            '.woocommerce-product-gallery img',
            '.product-gallery img',
            '.images img',
            '.woocommerce-product-gallery__image img',
            '.wp-post-image',
            '.attachment-shop_single',
            '.slideshow img',
            '.carousel img'
        ]
        
        all_images = []
        for pattern in image_patterns:
            images = soup.select(pattern)
            for img in images:
                # 过滤LOGO和图标
                if 'src' in img.attrs:
                    img_src = img['src']
                    if img_src.startswith('//'):
                        img_src = 'https:' + img_src
                    elif img_src.startswith('/'):
                        img_src = base_domain + img_src
                    if not self._is_logo_or_icon(img, img_src) and img_src not in all_images:
                        all_images.append(img_src)
                # 检查data-src属性（懒加载图片）
                if 'data-src' in img.attrs:
                    img_src = img['data-src']
                    if img_src.startswith('//'):
                        img_src = 'https:' + img_src
                    elif img_src.startswith('/'):
                        img_src = base_domain + img_src
                    if not self._is_logo_or_icon(img, img_src) and img_src not in all_images:
                        all_images.append(img_src)
                # 检查data-full-src属性（高清图片）
                if 'data-full-src' in img.attrs:
                    img_src = img['data-full-src']
                    if img_src.startswith('//'):
                        img_src = 'https:' + img_src
                    elif img_src.startswith('/'):
                        img_src = base_domain + img_src
                    if not self._is_logo_or_icon(img, img_src) and img_src not in all_images:
                        all_images.append(img_src)
        
        # 如果没有找到产品图片，尝试使用正则表达式从页面源码中提取
        if not all_images:
            # 查找所有img标签
            all_img_tags = soup.find_all('img')
            for img in all_img_tags:
                if 'src' in img.attrs:
                    img_src = img['src']
                    if img_src.startswith('//'):
                        img_src = 'https:' + img_src
                    elif img_src.startswith('/'):
                        img_src = base_domain + img_src
                    if not self._is_logo_or_icon(img, img_src) and img_src not in all_images:
                        all_images.append(img_src)
                if 'data-src' in img.attrs:
                    img_src = img['data-src']
                    if img_src.startswith('//'):
                        img_src = 'https:' + img_src
                    elif img_src.startswith('/'):
                        img_src = base_domain + img_src
                    if not self._is_logo_or_icon(img, img_src) and img_src not in all_images:
                        all_images.append(img_src)
        
        # 还可以从页面源码中查找背景图片
        bg_images = re.findall(r'background-image:\s*url\([\'"]?([^\'"]+)[\'"]?\)', str(soup))
        for img_src in bg_images:
            if img_src.startswith('//'):
                img_src = 'https:' + img_src
            elif img_src.startswith('/'):
                img_src = base_domain + img_src
            # 过滤可能的背景LOGO
            if not any(keyword in img_src.lower() for keyword in self.logo_filter['url_keywords']) and img_src not in all_images:
                all_images.append(img_src)
        
        # 设置主图片和所有图片
        product['images'] = all_images
        if all_images:
            product['image'] = all_images[0]  # 主图片使用第一张
        else:
            product['image'] = ""
        
        # 提取分类
        breadcrumbs = soup.select('.breadcrumb a, .navigation a')
        if breadcrumbs:
            product['categories'] = ','.join([a.text.strip() for a in breadcrumbs])
        else:
            product['categories'] = ""
        
        # 提取SKU
        sku_patterns = ['.sku', '[itemprop="sku"]', '.product-code']
        for pattern in sku_patterns:
            sku_elem = soup.select_one(pattern)
            if sku_elem:
                product['sku'] = sku_elem.text.strip()
                break
        
        if not product.get('sku'):
            # 从URL中提取可能的SKU
            sku_match = re.search(r'id=(\d+)', url)
            if sku_match:
                product['sku'] = f"BK-{sku_match.group(1)}"
            else:
                product['sku'] = ""
        
        # 其他必要字段
        product['url'] = url
        product['tags'] = ""
        product['scrape_time'] = time.strftime("%Y-%m-%d %H:%M:%S")
        
        # 如果是调试模式，保存HTML内容
        if self.debug_mode:
            try:
                with open("debug_page.html", "w", encoding="utf-8") as f:
                    f.write(str(soup))
            except:
                pass
        
        return product
        
    def _extract_product_data(self, soup, url):
        """从页面提取商品数据"""
        # 特殊处理bkhorsebag网站
        if 'bkhorsebag' in url:
            return self._extract_product_data_bkhorsebag(soup, url)
        
        # 获取基础URL用于处理相对路径
        base_url = urlparse(url)
        base_domain = f"{base_url.scheme}://{base_url.netloc}"
        
        product = {}
        
        # 尝试多种方式获取名称
        name_selectors = [
            self.selectors['name'],
            'h1',
            '.product-title',
            '.product_name',
            '.product-name',
            '#product_title',
            'title'
        ]
        
        for selector in name_selectors:
            name_elem = soup.select_one(selector)
            if name_elem and name_elem.text.strip():
                product['name'] = name_elem.text.strip()
                break
                
        # 尝试多种方式获取价格
        price_selectors = [
            self.selectors['price'],
            '.price',
            '.product-price',
            '.price .amount',
            '.product_price',
            '#price',
            '.ht_price'
        ]
        
        for selector in price_selectors:
            price_elem = soup.select_one(selector)
            if price_elem and price_elem.text.strip():
                product['price'] = price_elem.text.strip()
                break
        
        # 获取描述
        description_elem = soup.select_one(self.selectors['description'])
        product['description'] = str(description_elem) if description_elem else ''
        
        # 获取多张图片
        product['images'] = []  # 存储多张图片
        
        # 首先使用配置的选择器查找图片
        images = soup.select(self.selectors['image'])
        for img in images:
            if 'src' in img.attrs:
                img_src = img['src']
                if img_src.startswith('//'):
                    img_src = 'https:' + img_src
                elif img_src.startswith('/'):
                    img_src = base_domain + img_src
                if not self._is_logo_or_icon(img, img_src) and img_src not in product['images']:
                    product['images'].append(img_src)
            # 检查data-src属性（懒加载图片）
            if 'data-src' in img.attrs:
                img_src = img['data-src']
                if img_src.startswith('//'):
                    img_src = 'https:' + img_src
                elif img_src.startswith('/'):
                    img_src = base_domain + img_src
                if not self._is_logo_or_icon(img, img_src) and img_src not in product['images']:
                    product['images'].append(img_src)
            # 检查data-large-file属性（WooCommerce高清图）
            if 'data-large-file' in img.attrs:
                img_src = img['data-large-file']
                if img_src.startswith('//'):
                    img_src = 'https:' + img_src
                elif img_src.startswith('/'):
                    img_src = base_domain + img_src
                if not self._is_logo_or_icon(img, img_src) and img_src not in product['images']:
                    product['images'].append(img_src)
        
        # 如果没有找到图片，尝试其他常见选择器
        if not product['images']:
            # 尝试其他常见图片选择器
            img_selectors = [
                '.product-image img', 
                '.main-image img', 
                '#product-image', 
                '.woocommerce-product-gallery__image img',
                '.product-gallery img',
                '.images img',
                '.gallery img',
                '.wp-post-image',
                '.attachment-shop_single'
            ]
            
            for img_selector in img_selectors:
                images = soup.select(img_selector)
                for img in images:
                    if 'src' in img.attrs:
                        img_src = img['src']
                        if img_src.startswith('//'):
                            img_src = 'https:' + img_src
                        elif img_src.startswith('/'):
                            img_src = base_domain + img_src
                        if not self._is_logo_or_icon(img, img_src) and img_src not in product['images']:
                            product['images'].append(img_src)
                    if 'data-src' in img.attrs:
                        img_src = img['data-src']
                        if img_src.startswith('//'):
                            img_src = 'https:' + img_src
                        elif img_src.startswith('/'):
                            img_src = base_domain + img_src
                        if not self._is_logo_or_icon(img, img_src) and img_src not in product['images']:
                            product['images'].append(img_src)
        
        # 如果仍然没有找到图片，尝试查找所有图片
        if not product['images']:
            all_img_tags = soup.find_all('img')
            for img in all_img_tags:
                # 排除小图标和装饰性图片
                if 'src' in img.attrs and not img['src'].endswith(('.ico', '.svg')):
                    if not any(x in img.get('class', []) for x in ['icon', 'logo', 'avatar']):
                        img_src = img['src']
                        if img_src.startswith('//'):
                            img_src = 'https:' + img_src
                        elif img_src.startswith('/'):
                            img_src = base_domain + img_src
                        if not self._is_logo_or_icon(img, img_src) and img_src not in product['images']:
                            product['images'].append(img_src)
        
        # 过滤掉小尺寸图片 (可能是缩略图或图标)
        filtered_images = []
        for img_url in product['images']:
            # 如果URL中包含尺寸信息
            if not any(x in img_url.lower() for x in ['thumb', '50x', '100x', 'icon', 'mini']):
                filtered_images.append(img_url)
        
        # 如果过滤后没有图片了，则使用原始列表
        if filtered_images:
            product['images'] = filtered_images
        
        # 设置主图片
        if product['images']:
            product['image'] = product['images'][0]
        else:
            product['image'] = ''
        
        # 获取分类
        categories = soup.select(self.selectors['categories'])
        product['categories'] = ','.join([cat.text.strip() for cat in categories]) if categories else ''
        
        # 获取标签
        tags = soup.select(self.selectors['tags'])
        product['tags'] = ','.join([tag.text.strip() for tag in tags]) if tags else ''
        
        # 获取SKU
        sku_elem = soup.select_one(self.selectors['sku'])
        product['sku'] = sku_elem.text.strip() if sku_elem else ''
        
        # 商品URL
        product['url'] = url
        
        # 采集时间
        product['scrape_time'] = time.strftime("%Y-%m-%d %H:%M:%S")
        
        return product
        
    def scrape_single_product(self, url, status_callback=None):
        """采集单个商品信息"""
        if status_callback:
            status_callback(f"正在获取: {url}")
        
        # 自动检测适用的选择器
        self.auto_detect_selectors(url)
            
        # 发送请求
        response = self._make_request(url, status_callback, self.timeout)
        if not response:
            return None
            
        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取商品数据
            product = self._extract_product_data(soup, url)
            
            # 验证商品数据
            if self._validate_product_data(product):
                self.products.append(product)
                if status_callback:
                    status_callback(f"成功获取商品: {product['name']}")
                return product
            else:
                # 特殊处理：如果是bkhorsebag网站但数据验证失败
                if 'bkhorsebag' in url:
                    # 确保至少有名称和价格
                    if not product.get('name'):
                        product['name'] = "BK Horse Product"
                    if not product.get('price'):
                        product['price'] = "价格待定"
                    
                    self.products.append(product)
                    if status_callback:
                        status_callback(f"成功获取商品: {product['name']} (数据部分填充)")
                    return product
                else:
                    error_msg = f"商品数据无效: {url}"
                    self.error_log.append(error_msg)
                    if status_callback:
                        status_callback(error_msg)
                    return None
                
        except Exception as e:
            error_msg = f"解析商品数据时出错: {url} - {str(e)}"
            self.error_log.append(error_msg)
            if status_callback:
                status_callback(error_msg)
            return None
    
    def _extract_product_links(self, soup, url):
        """从页面中提取商品链接"""
        product_links = []
        
        # 尝试使用配置的选择器
        links = soup.select(self.selectors['product_links'])
        if links:
            for link in links:
                if 'href' in link.attrs:
                    product_links.append(link['href'])
        
        # 如果没有找到链接，尝试一些常见的选择器
        if not product_links:
            common_selectors = [
                '.products .product a', 
                '.product-list a', 
                '.product-grid a', 
                '.product a', 
                '.products a',
                'a.product-title',
                '.item a',
                '.product-item a'
            ]
            
            for selector in common_selectors:
                links = soup.select(selector)
                for link in links:
                    if 'href' in link.attrs and '/product/' in link['href']:
                        product_links.append(link['href'])
            
            # 如果还是没有找到，尝试查找所有链接且URL中包含product关键词
            if not product_links:
                all_links = soup.select('a')
                for link in all_links:
                    if 'href' in link.attrs and ('/product/' in link['href'] or 'product_id' in link['href'] or 'id=' in link['href']):
                        product_links.append(link['href'])
        
        # 处理相对URL
        base_url = urlparse(url)
        base = f"{base_url.scheme}://{base_url.netloc}"
        
        # 转换相对URL为绝对URL
        for i in range(len(product_links)):
            if not product_links[i].startswith(('http://', 'https://')):
                if product_links[i].startswith('/'):
                    product_links[i] = base + product_links[i]
                else:
                    product_links[i] = base + '/' + product_links[i]
        
        # 去重
        product_links = list(set(product_links))
        
        return product_links
    
    def scrape_page_products(self, url, status_callback=None, progress_callback=None):
        """采集页面上的所有商品"""
        if status_callback:
            status_callback(f"正在获取页面: {url}")
            
        # 自动检测适用的选择器
        self.auto_detect_selectors(url)
        
        # 特殊处理bkhorsebag网站
        if 'bkhorsebag' in url:
            # 检查URL是否为分类页面
            if '/index.php?catid=' in url or '/products.html' in url:
                # 尝试发送请求
                response = self._make_request(url, status_callback, self.timeout)
                if not response:
                    # 如果请求失败，尝试直接作为产品页面处理
                    if status_callback:
                        status_callback(f"无法获取产品列表，尝试将当前页面作为产品页处理")
                    product = self.scrape_single_product(url, status_callback)
                    if product:
                        if status_callback:
                            status_callback(f"成功获取单个商品: {product['name']}")
                        return 1
                    else:
                        # 尝试访问首页获取产品链接
                        base_url = "https://www.bkhorsebag.com/"
                        if status_callback:
                            status_callback(f"尝试从首页获取产品链接: {base_url}")
                        return self._scrape_bkhorsebag_homepage(base_url, status_callback, progress_callback)
                
                try:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # 尝试查找所有可能的产品链接
                    product_links = []
                    
                    # 方法1: 查找所有包含产品ID的链接
                    links = soup.find_all('a', href=re.compile(r'id=\d+'))
                    for link in links:
                        href = link.get('href')
                        if href and 'id=' in href:
                            # 处理相对URL
                            if href.startswith('/'):
                                base_domain = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
                                href = base_domain + href
                            elif not href.startswith(('http://', 'https://')):
                                base_domain = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
                                href = base_domain + '/' + href
                            product_links.append(href)
                    
                    # 方法2: 查找所有可能的产品图片链接
                    if not product_links:
                        product_containers = soup.select('.product, .item, [class*="product"], [class*="item"]')
                        for container in product_containers:
                            links = container.find_all('a')
                            for link in links:
                                href = link.get('href')
                                if href:
                                    # 处理相对URL
                                    if href.startswith('/'):
                                        base_domain = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
                                        href = base_domain + href
                                    elif not href.startswith(('http://', 'https://')):
                                        base_domain = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
                                        href = base_domain + '/' + href
                                    product_links.append(href)
                    
                    # 方法3: 查找任何可能的链接
                    if not product_links:
                        all_links = soup.find_all('a')
                        for link in all_links:
                            href = link.get('href')
                            if href and ('product' in href.lower() or 'item' in href.lower() or 'id=' in href.lower()):
                                # 处理相对URL
                                if href.startswith('/'):
                                    base_domain = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
                                    href = base_domain + href
                                elif not href.startswith(('http://', 'https://')):
                                    base_domain = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
                                    href = base_domain + '/' + href
                                if href not in product_links:
                                    product_links.append(href)
                    
                    # 如果仍未找到产品链接，尝试从整个页面中查找任何可能的链接
                    if not product_links:
                        links = re.findall(r'href=[\'"]?([^\'" >]+)', response.text)
                        for href in links:
                            if 'id=' in href or 'product' in href.lower():
                                # 处理相对URL
                                if href.startswith('/'):
                                    base_domain = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
                                    href = base_domain + href
                                elif not href.startswith(('http://', 'https://')):
                                    base_domain = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
                                    href = base_domain + '/' + href
                                product_links.append(href)
                    
                    # 去重
                    product_links = list(set(product_links))
                    
                    # 如果仍然没有找到产品链接，直接尝试当前URL
                    if not product_links:
                        product_links = [url]
                        if status_callback:
                            status_callback(f"未找到产品链接，将当前页面作为产品页处理")
                    
                    if status_callback:
                        status_callback(f"找到 {len(product_links)} 个商品链接")
                    
                    # 采集每个商品
                    products_count = 0
                    for i, link in enumerate(product_links):
                        if progress_callback:
                            progress_callback(i, len(product_links))
                            
                        if status_callback:
                            status_callback(f"正在获取 ({i+1}/{len(product_links)}): {link}")
                            
                        product = self.scrape_single_product(link, status_callback)
                        if product:
                            products_count += 1
                        
                        # 随机间隔时间
                        sleep_time = random.uniform(self.request_interval[0], self.request_interval[1])
                        if status_callback:
                            status_callback(f"等待 {sleep_time:.1f} 秒...")
                        time.sleep(sleep_time)
                        
                    if status_callback:
                        status_callback(f"完成! 成功采集 {products_count}/{len(product_links)} 个商品")
                        
                    return products_count
                    
                except Exception as e:
                    error_msg = f"解析页面时出错: {url} - {str(e)}"
                    self.error_log.append(error_msg)
                    if status_callback:
                        status_callback(error_msg)
                        
                    # 尝试直接作为产品页处理
                    if status_callback:
                        status_callback(f"尝试将当前页面作为产品页处理")
                    product = self.scrape_single_product(url, status_callback)
                    if product:
                        if status_callback:
                            status_callback(f"成功获取单个商品: {product['name']}")
                        return 1
                    
                    return 0
                    
            # 如果不是分类页，直接当作单个商品页处理
            product = self.scrape_single_product(url, status_callback)
            if product:
                if status_callback:
                    status_callback(f"成功获取单个商品: {product['name']}")
                return 1
            else:
                return 0
            
        # 处理其他类型的网站
        # 发送请求
        response = self._make_request(url, status_callback, self.timeout)
        if not response:
            return 0
            
        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 获取所有商品链接
            product_links = self._extract_product_links(soup, url)
            
            if not product_links:
                error_msg = f"未找到商品链接，请检查选择器和URL: {url}"
                self.error_log.append(error_msg)
                if status_callback:
                    status_callback(error_msg)
                return 0
                
            if status_callback:
                status_callback(f"找到 {len(product_links)} 个商品链接")
            
            # 采集每个商品
            products_count = 0
            for i, link in enumerate(product_links):
                if progress_callback:
                    progress_callback(i, len(product_links))
                    
                if status_callback:
                    status_callback(f"正在获取 ({i+1}/{len(product_links)}): {link}")
                    
                product = self.scrape_single_product(link, status_callback)
                if product:
                    products_count += 1
                
                # 随机间隔时间
                sleep_time = random.uniform(self.request_interval[0], self.request_interval[1])
                if status_callback:
                    status_callback(f"等待 {sleep_time:.1f} 秒...")
                time.sleep(sleep_time)
                
            if status_callback:
                status_callback(f"完成! 成功采集 {products_count}/{len(product_links)} 个商品")
                
            return products_count
            
        except Exception as e:
            error_msg = f"采集页面商品时出错: {url} - {str(e)}"
            self.error_log.append(error_msg)
            if status_callback:
                status_callback(error_msg)
            return 0
            
    def _scrape_bkhorsebag_homepage(self, url, status_callback=None, progress_callback=None):
        """专门处理bkhorsebag.com网站首页的产品链接提取"""
        if status_callback:
            status_callback(f"尝试从bkhorsebag首页获取产品链接: {url}")
            
        # 发送请求
        response = self._make_request(url, status_callback, self.timeout)
        if not response:
            return 0
            
        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找所有可能的产品链接
            product_links = []
            
            # 1. 查找所有包含id=的链接 (bkhorsebag常用产品URL格式)
            links = soup.find_all('a', href=re.compile(r'id=\d+'))
            for link in links:
                href = link.get('href')
                if href:
                    # 处理相对URL
                    if href.startswith('/'):
                        base_domain = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
                        href = base_domain + href
                    elif not href.startswith(('http://', 'https://')):
                        base_domain = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
                        href = base_domain + '/' + href
                    product_links.append(href)
            
            # 2. 查找所有图片链接的父a标签
            if not product_links:
                img_tags = soup.find_all('img')
                for img in img_tags:
                    parent_a = img.find_parent('a')
                    if parent_a and parent_a.has_attr('href'):
                        href = parent_a['href']
                        # 过滤可能的产品链接
                        if 'id=' in href or 'product' in href.lower():
                            # 处理相对URL
                            if href.startswith('/'):
                                base_domain = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
                                href = base_domain + href
                            elif not href.startswith(('http://', 'https://')):
                                base_domain = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
                                href = base_domain + '/' + href
                            product_links.append(href)
            
            # 去重
            product_links = list(set(product_links))
            
            # 如果找不到产品链接，尝试从HTML源码中提取
            if not product_links:
                # 从源码中查找所有href属性
                links = re.findall(r'href=[\'"]?([^\'" >]+)', response.text)
                for href in links:
                    if 'id=' in href or 'product' in href.lower():
                        # 处理相对URL
                        if href.startswith('/'):
                            base_domain = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
                            href = base_domain + href
                        elif not href.startswith(('http://', 'https://')):
                            base_domain = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
                            href = base_domain + '/' + href
                        product_links.append(href)
                
                # 去重
                product_links = list(set(product_links))
            
            # 如果仍然没有找到产品链接，使用预定义的URL模式
            if not product_links:
                # 使用常见的产品ID范围生成URL
                base_domain = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
                for i in range(1, 30):  # 尝试1-30的产品ID
                    product_links.append(f"{base_domain}/index.php?id={i}")
                
                if status_callback:
                    status_callback(f"未找到产品链接，使用预生成的产品URL")
            
            if status_callback:
                status_callback(f"找到 {len(product_links)} 个可能的商品链接")
            
            # 采集每个商品
            products_count = 0
            for i, link in enumerate(product_links):
                if progress_callback:
                    progress_callback(i, len(product_links))
                    
                if status_callback:
                    status_callback(f"正在获取 ({i+1}/{len(product_links)}): {link}")
                    
                product = self.scrape_single_product(link, status_callback)
                if product:
                    products_count += 1
                
                # 随机间隔时间
                sleep_time = random.uniform(self.request_interval[0], self.request_interval[1])
                if status_callback:
                    status_callback(f"等待 {sleep_time:.1f} 秒...")
                time.sleep(sleep_time)
                
            if status_callback:
                status_callback(f"完成! 成功采集 {products_count}/{len(product_links)} 个商品")
                
            return products_count
            
        except Exception as e:
            error_msg = f"从bkhorsebag首页采集商品时出错: {url} - {str(e)}"
            self.error_log.append(error_msg)
            if status_callback:
                status_callback(error_msg)
            return 0

    def export_to_csv(self, filename):
        """导出商品信息到CSV文件"""
        if not self.products:
            return False
            
        try:
            # 获取所有可能的字段名
            all_fields = set()
            for product in self.products:
                all_fields.update(product.keys())
            
            # 移除'images'字段(因为它是数组，不适合直接放在CSV中)
            if 'images' in all_fields:
                all_fields.remove('images')
            
            # 转换为有序列表
            fieldnames = list(all_fields)
            
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for product in self.products:
                    # 创建一个新字典，去掉images字段
                    product_copy = {k: v for k, v in product.items() if k != 'images'}
                    writer.writerow(product_copy)
            return True
        except Exception as e:
            error_msg = f"导出CSV时出错: {str(e)}"
            self.error_log.append(error_msg)
            return False
            
    def export_to_txt(self, filename):
        """导出商品信息到TXT文件"""
        if not self.products:
            return False
            
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                for product in self.products:
                    for key, value in product.items():
                        if key == 'images':
                            f.write(f"{key}:\n")
                            for i, img_url in enumerate(value):
                                f.write(f"  {i+1}. {img_url}\n")
                        else:
                            f.write(f"{key}: {value}\n")
                    f.write("\n" + "-"*50 + "\n\n")
            return True
        except Exception as e:
            error_msg = f"导出TXT时出错: {str(e)}"
            self.error_log.append(error_msg)
            return False
    
    def export_to_json(self, filename):
        """导出商品信息到JSON文件"""
        if not self.products:
            return False
            
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.products, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            error_msg = f"导出JSON时出错: {str(e)}"
            self.error_log.append(error_msg)
            return False
            
    def clear_products(self):
        """清空已采集的商品"""
        self.products = []

    # 添加图片下载控制方法
    def set_download_images(self, enabled=True):
        """设置是否下载图片"""
        self.download_images = enabled
        return True
        
    def set_image_folder(self, folder_path):
        """设置图片保存文件夹"""
        self.image_folder = folder_path
        if not os.path.exists(self.image_folder):
            os.makedirs(self.image_folder)
        return True
    
    # 添加图片下载方法
    def _download_image(self, image_url, product_name, index=0):
        """下载图片并返回本地路径"""
        if not image_url:
            return ""
            
        try:
            # 清理URL
            image_url = image_url.strip()
            
            # 检查是否已下载过该图片
            if image_url in self.downloaded_images:
                return self.downloaded_images[image_url]
                
            # 生成文件名
            file_extension = os.path.splitext(urlparse(image_url).path)[1]
            if not file_extension:
                file_extension = '.jpg'  # 默认扩展名
                
            # 生成唯一文件名
            safe_name = re.sub(r'[^\w\-_]', '_', product_name)  # 过滤掉不安全的字符
            filename = f"{safe_name}_{index}{file_extension}"
            file_path = os.path.join(self.image_folder, filename)
            
            # 下载图片
            response = self._make_request(image_url)
            if response and response.status_code == 200:
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                    
                # 保存下载记录
                self.downloaded_images[image_url] = file_path
                return file_path
                
        except Exception as e:
            error_msg = f"下载图片失败: {image_url} - {str(e)}"
            self.error_log.append(error_msg)
            
        return ""
    
    # 更新export_to_csv方法以支持WordPress导入
    def export_to_woocommerce_csv(self, filename):
        """导出为WooCommerce可导入的CSV格式，完全匹配WordPress导入格式"""
        if not self.products:
            return False
            
        try:
            # WooCommerce中文字段名
            woo_fields = [
                'ID', '类型', 'SKU', 'GTIN, UPC, EAN, or ISBN', '名称', '已发布', '是推荐产品？', 
                '在列表页可见', '简短描述', '描述', '促销开始日期', '促销截止日期', '税状态', '税类', 
                '有货？', '库存', '库存不足', '允许缺货下单？', '单独出售？', '重量(公斤)', '长度(厘米)', 
                '宽度 (厘米)', '高度 (厘米)', '允许客户评价？', '购物备注', '促销价格', '常规售价',
                '分类', '标签', '运费类', '图片', '下载限制', '下载的过期天数', '父级', '分组产品',
                '交叉销售', '交叉销售', '外部链接', '按钮文本', '位置', '品牌'
            ]
            
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=woo_fields)
                writer.writeheader()
                
                for product in self.products:
                    woo_product = {field: '' for field in woo_fields}  # 初始化所有字段为空字符串
                    
                    # 填充必要字段
                    woo_product['类型'] = 'simple'  # 简单商品类型
                    woo_product['已发布'] = '1'
                    woo_product['是推荐产品？'] = '0'
                    woo_product['在列表页可见'] = 'visible'
                    woo_product['有货？'] = '1'
                    woo_product['允许客户评价？'] = '1'
                    
                    # 过滤产品名称中的多余内容
                    product_name = product.get('name', '')
                    # 移除常见的多余后缀
                    suffixes_to_remove = [
                        "- KELLY - 产品 - BKHORSE",
                        "- KELLY",
                        "- 产品 - BKHORSE",
                        "- BKHORSE",
                        " - KELLY - 产品 - BKHORSE"
                    ]
                    for suffix in suffixes_to_remove:
                        if product_name.endswith(suffix):
                            product_name = product_name[:-(len(suffix))]
                    
                    woo_product['名称'] = product_name.strip()
                    
                    # 描述
                    about_us = """ABOUT US | BKHORSE
一家專注Handmade手袋12年的店鋪.
我們是你購買包袋的不二之選！
A Shop Focused on handmade bag for 12 years.
BKHORSE is your best option to buy bags.
Top private ordering for you."""
                    
                    woo_product['简短描述'] = about_us
                    
                    # 生成HTML描述
                    description = f"""<h3>{product_name.strip()}</h3>
<h4>規格:</h4>
<p style="font-weight: 400;">{product_name.strip().replace('Kelly', '凱莉包')}</p>

<h4>介紹:</h4>
<p style="font-weight: 400;">Top craftsman made！</p>
<p style="font-weight: 400;">With the best quality！</p>
<p style="font-weight: 400;">With the highest grade service !</p>
<p style="font-weight: 400;">BKHORSE will be your dream store to buy handicraft bag!!!</p>
<p style="font-weight: 400;">-</p>
<p style="font-weight: 400;">20年工齡老工匠精心手工縫製！</p>
<p style="font-weight: 400;">頂尖的匠心品质舆服務！</p>
<p style="font-weight: 400;">您可以永远相信我们！</p>
<p style="font-weight: 400;">BKHORSE是您購買手縫包袋的最佳選擇！</p>"""
                    
                    woo_product['描述'] = description
                    
                    # 价格处理
                    price_text = product.get('price', '')
                    # 尝试提取数字部分
                    price_match = re.search(r'[\d\.,]+', price_text)
                    if price_match:
                        price = price_match.group(0).replace(',', '')
                        # 生成两个价格，常规价略高一些
                        regular_price = float(price) + 100
                        woo_product['常规售价'] = str(regular_price)
                        woo_product['促销价格'] = price
                    
                    # SKU
                    woo_product['SKU'] = product.get('sku', '')
                    
                    # 分类和标签
                    category_text = product_name
                    bag_type = "Bag"
                    leather_type = "Epsom"  # 默认皮革类型
                    
                    # 从名称中提取可能的皮革类型
                    if "Swift" in category_text:
                        leather_type = "Swift"
                    elif "Epsom" in category_text:
                        leather_type = "Epsom"
                    elif "Togo" in category_text:
                        leather_type = "Togo"
                    elif "Box" in category_text:
                        leather_type = "Box"
                    elif "Chevre" in category_text:
                        leather_type = "Chevre"
                    elif "Niloticus" in category_text:
                        leather_type = "Shiny Niloticus"
                    
                    # 构建分类
                    size = "Kelly 25" if "25" in category_text else "Kelly"
                    categories = f"{bag_type}, {leather_type}, {size}"
                    woo_product['分类'] = categories
                    
                    # 标签使用皮革类型
                    woo_product['标签'] = leather_type
                    
                    # 处理图片 - 直接使用原始URL
                    image_urls = []
                    
                    # 根据是否有多张图片选择处理方法
                    if 'images' in product and product['images']:
                        image_urls = product['images']
                    elif 'image' in product and product['image']:
                        image_urls = [product['image']]
                    
                    # 确保至少有一张图片重复出现，模仿示例中的模式
                    if image_urls and len(image_urls) > 0:
                        image_urls.insert(1, image_urls[0])
                    
                    # 在WooCommerce中使用原始URL，以逗号分隔，无空格
                    woo_product['图片'] = ', '.join(image_urls)
                    
                    writer.writerow(woo_product)
                    
            return True
        except Exception as e:
            error_msg = f"导出WooCommerce CSV时出错: {str(e)}"
            self.error_log.append(error_msg)
            return False

    def split_and_export_for_woocommerce(self, folder_path, products_per_file=5):
        """将商品数据拆分为多个小文件，每个文件包含指定数量的商品，适合WordPress导入"""
        if not self.products:
            return False
        
        try:
            # 创建导出目录
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
            
            # WooCommerce中文字段名
            woo_fields = [
                'ID', '类型', 'SKU', 'GTIN, UPC, EAN, or ISBN', '名称', '已发布', '是推荐产品？', 
                '在列表页可见', '简短描述', '描述', '促销开始日期', '促销截止日期', '税状态', '税类', 
                '有货？', '库存', '库存不足', '允许缺货下单？', '单独出售？', '重量(公斤)', '长度(厘米)', 
                '宽度 (厘米)', '高度 (厘米)', '允许客户评价？', '购物备注', '促销价格', '常规售价',
                '分类', '标签', '运费类', '图片', '下载限制', '下载的过期天数', '父级', '分组产品',
                '交叉销售', '交叉销售', '外部链接', '按钮文本', '位置', '品牌'
            ]
            
            # 计算需要创建的文件数量
            total_products = len(self.products)
            num_files = (total_products + products_per_file - 1) // products_per_file  # 向上取整
            
            exported_files = []
            
            # 按批次创建文件
            for i in range(num_files):
                start_idx = i * products_per_file
                end_idx = min((i + 1) * products_per_file, total_products)
                batch_products = self.products[start_idx:end_idx]
                
                # 创建文件名
                file_name = f"products_batch_{i+1}.csv"
                file_path = os.path.join(folder_path, file_name)
                
                with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.DictWriter(f, fieldnames=woo_fields)
                    writer.writeheader()
                    
                    for product in batch_products:
                        woo_product = {field: '' for field in woo_fields}  # 初始化所有字段为空字符串
                        
                        # 填充必要字段
                        woo_product['类型'] = 'simple'  # 简单商品类型
                        woo_product['已发布'] = '1'
                        woo_product['是推荐产品？'] = '0'
                        woo_product['在列表页可见'] = 'visible'
                        woo_product['有货？'] = '1'
                        woo_product['允许客户评价？'] = '1'
                        
                        # 过滤产品名称中的多余内容
                        product_name = product.get('name', '')
                        # 移除常见的多余后缀
                        suffixes_to_remove = [
                            "- KELLY - 产品 - BKHORSE",
                            "- KELLY",
                            "- 产品 - BKHORSE",
                            "- BKHORSE",
                            " - KELLY - 产品 - BKHORSE"
                        ]
                        for suffix in suffixes_to_remove:
                            if product_name.endswith(suffix):
                                product_name = product_name[:-(len(suffix))]
                        
                        woo_product['名称'] = product_name.strip()
                        
                        # 描述
                        about_us = """ABOUT US | BKHORSE
一家專注Handmade手袋12年的店鋪.
我們是你購買包袋的不二之選！
A Shop Focused on handmade bag for 12 years.
BKHORSE is your best option to buy bags.
Top private ordering for you."""
                        
                        woo_product['简短描述'] = about_us
                        
                        # 生成HTML描述
                        description = f"""<h3>{product_name.strip()}</h3>
<h4>規格:</h4>
<p style="font-weight: 400;">{product_name.strip().replace('Kelly', '凱莉包')}</p>

<h4>介紹:</h4>
<p style="font-weight: 400;">Top craftsman made！</p>
<p style="font-weight: 400;">With the best quality！</p>
<p style="font-weight: 400;">With the highest grade service !</p>
<p style="font-weight: 400;">BKHORSE will be your dream store to buy handicraft bag!!!</p>
<p style="font-weight: 400;">-</p>
<p style="font-weight: 400;">20年工齡老工匠精心手工縫製！</p>
<p style="font-weight: 400;">頂尖的匠心品质舆服務！</p>
<p style="font-weight: 400;">您可以永远相信我们！</p>
<p style="font-weight: 400;">BKHORSE是您購買手縫包袋的最佳選擇！</p>"""
                        
                        woo_product['描述'] = description
                        
                        # 价格处理
                        price_text = product.get('price', '')
                        # 尝试提取数字部分
                        price_match = re.search(r'[\d\.,]+', price_text)
                        if price_match:
                            price = price_match.group(0).replace(',', '')
                            # 生成两个价格，常规价略高一些
                            regular_price = float(price) + 100
                            woo_product['常规售价'] = str(regular_price)
                            woo_product['促销价格'] = price
                        
                        # SKU
                        woo_product['SKU'] = product.get('sku', '')
                        
                        # 分类和标签
                        category_text = product_name
                        bag_type = "Bag"
                        leather_type = "Epsom"  # 默认皮革类型
                        
                        # 从名称中提取可能的皮革类型
                        if "Swift" in category_text:
                            leather_type = "Swift"
                        elif "Epsom" in category_text:
                            leather_type = "Epsom"
                        elif "Togo" in category_text:
                            leather_type = "Togo"
                        elif "Box" in category_text:
                            leather_type = "Box"
                        elif "Chevre" in category_text:
                            leather_type = "Chevre"
                        elif "Niloticus" in category_text:
                            leather_type = "Shiny Niloticus"
                        
                        # 构建分类
                        size = "Kelly 25" if "25" in category_text else "Kelly"
                        categories = f"{bag_type}, {leather_type}, {size}"
                        woo_product['分类'] = categories
                        
                        # 标签使用皮革类型
                        woo_product['标签'] = leather_type
                        
                        # 处理图片 - 直接使用原始URL
                        image_urls = []
                        
                        # 根据是否有多张图片选择处理方法
                        if 'images' in product and product['images']:
                            image_urls = product['images']
                        elif 'image' in product and product['image']:
                            image_urls = [product['image']]
                            
                        # 确保至少有一张图片重复出现，模仿示例中的模式
                        if image_urls and len(image_urls) > 0:
                            image_urls.insert(1, image_urls[0])
                        
                        # 在WooCommerce中使用原始URL，以逗号分隔，无空格
                        woo_product['图片'] = ', '.join(image_urls)
                        
                        writer.writerow(woo_product)
                
                exported_files.append(file_path)
            
            # 创建一个README文件，说明如何导入
            readme_path = os.path.join(folder_path, "导入说明.txt")
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write("WordPress导入说明\n")
                f.write("================\n\n")
                f.write("由于WordPress通常有上传文件大小限制，数据已被拆分为多个小文件便于导入。\n\n")
                f.write("导入步骤：\n")
                f.write("1. 进入WordPress后台 > 产品 > 导入\n")
                f.write("2. 逐个上传这些CSV文件\n")
                f.write("3. 上传顺序不重要，每个文件包含不同的商品\n\n")
                f.write(f"共拆分为{num_files}个文件，每个文件包含不超过{products_per_file}个商品\n\n")
                f.write("图片导入说明：\n")
                f.write("- CSV中包含的是图片的URL链接，WordPress将直接从这些URL下载图片\n")
                f.write("- 确保WordPress服务器可以访问这些图片URL\n")
                f.write("- 数据格式已完全按照WordPress WooCommerce标准格式生成\n\n")
                f.write("注意事项：\n")
                f.write("- 如需增大导入文件大小限制，请修改服务器的php.ini配置\n")
                f.write("- 需要修改的配置项: upload_max_filesize, post_max_size\n")
            
            # 导出HTML预览文件，帮助用户查看采集结果
            self._export_preview_html(folder_path)
            
            return exported_files
        
        except Exception as e:
            error_msg = f"分批导出CSV时出错: {str(e)}"
            self.error_log.append(error_msg)
            return False
        
    def _export_preview_html(self, folder_path):
        """导出HTML预览文件，用于查看采集结果"""
        try:
            preview_path = os.path.join(folder_path, "采集结果预览.html")
            with open(preview_path, 'w', encoding='utf-8') as f:
                f.write("<!DOCTYPE html>\n")
                f.write("<html lang='zh-CN'>\n")
                f.write("<head>\n")
                f.write("    <meta charset='UTF-8'>\n")
                f.write("    <meta name='viewport' content='width=device-width, initial-scale=1.0'>\n")
                f.write("    <title>采集商品预览</title>\n")
                f.write("    <style>\n")
                f.write("        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }\n")
                f.write("        .product { border: 1px solid #ddd; margin: 20px 0; padding: 15px; border-radius: 5px; }\n")
                f.write("        .product h2 { margin-top: 0; color: #333; }\n")
                f.write("        .product-info { margin-bottom: 15px; }\n")
                f.write("        .product-price { font-weight: bold; color: #e63946; }\n")
                f.write("        .product-gallery { display: flex; flex-wrap: wrap; gap: 10px; }\n")
                f.write("        .product-gallery img { max-width: 150px; max-height: 150px; object-fit: cover; border: 1px solid #eee; }\n")
                f.write("    </style>\n")
                f.write("</head>\n")
                f.write("<body>\n")
                f.write("    <h1>采集商品预览</h1>\n")
                f.write(f"    <p>共采集到 {len(self.products)} 个商品</p>\n")
                
                for product in self.products:
                    f.write("    <div class='product'>\n")
                    f.write(f"        <h2>{product.get('name', '无名称')}</h2>\n")
                    f.write("        <div class='product-info'>\n")
                    f.write(f"            <p><strong>价格:</strong> <span class='product-price'>{product.get('price', '未知')}</span></p>\n")
                    f.write(f"            <p><strong>SKU:</strong> {product.get('sku', '无SKU')}</p>\n")
                    f.write(f"            <p><strong>分类:</strong> {product.get('categories', '无分类')}</p>\n")
                    f.write("        </div>\n")
                    
                    f.write("        <div class='product-gallery'>\n")
                    if 'images' in product and product['images']:
                        for img_url in product['images']:
                            f.write(f"            <img src='{img_url}' alt='商品图片'>\n")
                    elif 'image' in product and product['image']:
                        f.write(f"            <img src='{product['image']}' alt='商品图片'>\n")
                    else:
                        f.write("            <p>无图片</p>\n")
                    f.write("        </div>\n")
                    f.write("    </div>\n")
                
                f.write("</body>\n")
                f.write("</html>\n")
        
        except Exception as e:
            error_msg = f"导出预览HTML时出错: {str(e)}"
            self.error_log.append(error_msg)
            return False