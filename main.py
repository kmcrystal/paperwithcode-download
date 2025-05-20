#! /usr/bin/env python
# -*-coding:utf-8-*-
import os
import subprocess
import requests
from lxml import etree
from tqdm import tqdm
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import re
import hashlib
import urllib3
import shutil

BASE_URL = "https://paperswithcode.com/task/time-series-anomaly-detection"
BASE_DOWNLOAD_DIR = "paper-download_TimeSeriesAnomaly"

# 代理设置
proxies = {
    'http': 'http://localhost:7890',
    'https': 'http://localhost:7890'
}

# 不使用代理的会话（用于下载PDF）
no_proxy_session = requests.Session()
no_proxy_session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
})

# 使用代理的会话（用于访问paperswithcode）
proxy_session = requests.Session()
proxy_session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
})
proxy_session.proxies.update(proxies)

def create_session(use_proxy=True):
    session = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })
    if use_proxy:
        session.proxies.update(proxies)
    return session

def sanitize_filename(name, max_length=50):
    """清理文件名，移除非法字符并限制长度"""
    if not name:
        return "untitled_paper"
    
    # 清理文件名
    name = str(name)
    # 移除特殊字符
    name = re.sub(r'[<>:"/\\|?*\x00-\x1F]', '_', name)
    # 将多个空格替换为单个空格
    name = re.sub(r'\s+', ' ', name)
    # 将多个下划线替换为单个下划线
    name = re.sub(r'_+', '_', name)
    # 移除首尾的下划线、空格和点
    name = name.strip('_ .')
    
    if not name:
        name = "untitled_paper"
    
    # 如果文件名太长，只保留前30个字符，并确保不以空格或点结尾
    if len(name) > max_length:
        name = name[:max_length].strip('_ .')
    
    return name

def download_file(url, save_path, file_type, max_retries=3):
    """下载文件并保存到指定路径"""
    if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
        print(f"      [INFO] {file_type} already exists: {os.path.basename(save_path)}")
        return True

    # 创建无代理的HTTP连接池
    http = urllib3.PoolManager(
        timeout=urllib3.Timeout(connect=5.0, read=60.0),
        retries=urllib3.Retry(3),
        maxsize=10
    )
    
    for attempt in range(max_retries):
        try:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            print(f"      Downloading {file_type} from: {url}")
            
            # 使用urllib3直接下载
            response = http.request('GET', url, preload_content=False)
            
            if response.status != 200:
                raise Exception(f"HTTP {response.status}")
            
            total_size = int(response.headers.get('content-length', 0))
            with open(save_path, 'wb') as f, tqdm(
                desc=f"      Downloading {file_type}",
                total=total_size,
                unit='iB',
                unit_scale=True,
                unit_divisor=1024,
                leave=False
            ) as bar:
                while True:
                    chunk = response.read(1024*4)
                    if not chunk:
                        break
                    f.write(chunk)
                    bar.update(len(chunk))
            
            response.release_conn()
            print(f"      Successfully downloaded {file_type}")
            return True
            
        except Exception as e:
            print(f"      [ERROR] Download failed (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                return False
    return False

def process_github_url(url):
    """处理GitHub URL，转换为正确的仓库URL"""
    if not url or not isinstance(url, str):
        return None
    url = url.split('?')[0].split('#')[0]
    
    match = re.match(r'https?://github\.com/([^/]+/[^/]+)(?:/tree/[^/]+|/blob/[^/]+)?/?', url)
    if match:
        repo_path = match.group(1)
        if repo_path.endswith('.git'):
            return f'https://github.com/{repo_path}'
        return f'https://github.com/{repo_path}.git'
    
    if url.startswith('https://github.com/') and '/' in url.split('github.com/')[1] and not url.endswith('.git'):
        path_parts = url.split('github.com/')[1].split('/')
        if len(path_parts) == 2:
            return url + '.git'
    return url

def clone_repository(repo_url, save_path, max_retries=3):
    """克隆GitHub仓库"""
    processed_url = process_github_url(repo_url)
    if not processed_url or not processed_url.endswith('.git'):
        print(f"      [WARN] Invalid GitHub URL: {repo_url}")
        return False
        
    if os.path.exists(os.path.join(save_path, ".git")):
        print(f"      [INFO] Repository already exists: {save_path}")
        return True
    if os.path.exists(save_path) and os.listdir(save_path):
        print(f"      [WARN] Directory exists but not a git repo: {save_path}")
        return False
        
    os.makedirs(save_path, exist_ok=True)
    
    for attempt in range(max_retries):
        try:
            print(f"      Cloning repository: {processed_url}")
            result = subprocess.run(
                ['git', 'clone', '--depth', '1', processed_url, save_path],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                print(f"      Repository cloned successfully")
                return True
            else:
                print(f"      [ERROR] Clone failed: {result.stderr.strip()}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    return False
        except Exception as e:
            print(f"      [ERROR] Clone error (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                return False
    return False

def get_paper_details(session, paper_url):
    """获取论文详细信息"""
    try:
        response = session.get(paper_url, timeout=30)
        response.raise_for_status()
        html = etree.HTML(response.content)
        
        # 获取PDF链接
        pdf_url = None
        pdf_elements = html.xpath("//a[contains(@href, '.pdf')]/@href")
        if pdf_elements:
            pdf_url = pdf_elements[0]
            if pdf_url.startswith('//'):
                pdf_url = "https:" + pdf_url
            elif pdf_url.startswith('/'):
                pdf_url = "https://arxiv.org" + pdf_url
        
        # 获取代码仓库链接
        code_url = None
        code_elements = html.xpath("//a[contains(@href, 'github.com')]/@href")
        if code_elements:
            code_url = code_elements[0]
        
        return pdf_url, code_url
    except Exception as e:
        print(f"      [ERROR] Failed to get paper details: {e}")
        return None, None

def process_paper(session, title, paper_url):
    """处理单篇论文"""
    try:
        print(f"\n    Processing paper: {title}")
        print(f"      Fetching details from: {paper_url}")
        
        pdf_url, code_url = get_paper_details(session, paper_url)
        
        # 为文件夹和PDF文件使用不同的文件名长度限制
        folder_name = sanitize_filename(title, max_length=50)
        pdf_name = sanitize_filename(title, max_length=30)
        
        # 确保文件夹名不以点结尾
        if folder_name.endswith('.'):
            folder_name = folder_name[:-1]
        
        paper_dir = os.path.join(BASE_DOWNLOAD_DIR, folder_name)
        os.makedirs(paper_dir, exist_ok=True)
        
        if pdf_url:
            pdf_path = os.path.join(paper_dir, f"{pdf_name}.pdf")
            download_file(pdf_url, pdf_path, "PDF")
        else:
            print("      [WARN] PDF URL not found")
        
        if code_url:
            code_dir = os.path.join(paper_dir, "code")
            clone_repository(code_url, code_dir)
        else:
            print("      [INFO] Code URL not found")
        
        return True
    except Exception as e:
        print(f"      [ERROR] Failed to process paper: {e}")
        return False

def get_papers_from_page(session, page_num):
    """获取页面上的论文列表"""
    try:
        url = f"{BASE_URL}?page={page_num}"
        print(f"\n  Fetching page {page_num}: {url}")
        
        response = session.get(url, timeout=30)
        response.raise_for_status()
        html = etree.HTML(response.content)
        
        papers = []
        paper_elements = html.xpath("//div[contains(@class, 'paper-card')]")
        
        for element in paper_elements:
            try:
                title_element = element.xpath(".//h1/a | .//h5/a")[0]
                title = title_element.text.strip()
                paper_url = "https://paperswithcode.com" + title_element.get('href')
                papers.append((title, paper_url))
            except Exception as e:
                print(f"      [ERROR] Failed to parse paper element: {e}")
                continue
        
        return papers
    except Exception as e:
        print(f"  [ERROR] Failed to fetch page {page_num}: {e}")
        return []

if __name__ == '__main__':
    os.makedirs(BASE_DOWNLOAD_DIR, exist_ok=True)
    session = create_session(use_proxy=True)
    
    page_num = 1
    processed_titles = set()
    consecutive_empty_pages = 0
    
    while True:
        papers = get_papers_from_page(session, page_num)
        
        if not papers:
            consecutive_empty_pages += 1
            if consecutive_empty_pages >= 3:
                print("\n  No new papers found for 3 consecutive pages. Stopping.")
                break
        else:
            consecutive_empty_pages = 0
            new_papers = 0
            
            for title, paper_url in papers:
                if title not in processed_titles:
                    if process_paper(session, title, paper_url):
                        processed_titles.add(title)
                        new_papers += 1
                time.sleep(1)
            
            if new_papers == 0 and papers:
                print("\n  All papers on this page were already processed. Stopping.")
                break
        
        print(f"\n  Page {page_num} completed. Total unique papers: {len(processed_titles)}")
        page_num += 1
        time.sleep(2)
        
        if page_num > 200:
            print("\n  [WARN] Reached maximum page limit. Stopping.")
            break
    
    print(f"\n--- Script finished. Total unique papers processed: {len(processed_titles)} ---")
