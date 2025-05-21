# Papers with Code 论文下载工具

这是一个用于从 Papers with Code 网站批量下载论文及其代码的工具。该工具可以下载任意领域的论文，默认下载时间序列异常检测（Time Series Anomaly Detection）领域的论文，可以自动下载论文PDF文件并克隆相关的代码仓库。

## 功能特点

- 支持下载任意领域的论文
- 自动爬取 Papers with Code 网站上的论文信息
- 支持批量下载论文PDF文件
- 自动克隆论文相关的GitHub代码仓库
- 智能处理文件名，避免非法字符
- 支持断点续传，避免重复下载
- 详细的下载进度显示
- 完善的错误处理和重试机制

## 环境要求

- Python 3.6+
- Git
- 网络连接（建议使用代理）

## 安装步骤

1. 克隆仓库：
```bash
git clone https://github.com/kmcrystal/paperwithcode-download.git
cd paperwithcode-download
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

## 使用方法

1. 配置代理（可选）：
   如果你需要使用代理，请修改代码中的代理设置：
   ```python
   proxies = {
       'http': 'http://your-proxy:port',
       'https': 'http://your-proxy:port'
   }
   ```

2. 修改下载领域（可选）：
   如果你想下载其他领域的论文，请修改代码中的 `BASE_URL` 变量：
   ```python
   # 默认下载时间序列异常检测的论文
   BASE_URL = "https://paperswithcode.com/task/time-series-anomaly-detection"
   
   # 修改为其他领域，例如：
   # 目标检测
   BASE_URL = "https://paperswithcode.com/task/object-detection"
   # 图像分类
   BASE_URL = "https://paperswithcode.com/task/image-classification"
   # 自然语言处理
   BASE_URL = "https://paperswithcode.com/task/natural-language-processing"
   ```
   
   所有可用的任务名称可以在 https://paperswithcode.com/tasks 查看。

3. 运行脚本：
```bash
python man.py
```

4. 查看结果：
   下载的论文和代码将保存在 `paper-download_TimeSeriesAnomaly` 目录下，每篇论文都有独立的文件夹。

## 文件保存默认目录结构

```
paper-download_TimeSeriesAnomaly/
├── paper-title-1/
│   ├── paper-title-1.pdf
│   └── code/
│       └── [GitHub仓库内容]
├── paper-title-2/
│   ├── paper-title-2.pdf
│   └── code/
│       └── [GitHub仓库内容]
└── ...
```

## 注意事项

1. 请确保有足够的磁盘空间
2. 下载大量文件可能需要较长时间
3. 部分论文可能没有公开的PDF或代码
4. 建议使用稳定的网络连接
5. 如果遇到下载失败，程序会自动重试

## 常见问题

1. Q: 下载速度很慢怎么办？
   A: 可以尝试使用代理或调整代码中的超时设置

2. Q: 如何下载其他领域的论文？
   A: 修改代码中的 `BASE_URL` 变量，指向目标领域的URL。例如：
   ```python
   # 下载目标检测领域的论文
   BASE_URL = "https://paperswithcode.com/task/object-detection"
   ```
   所有可用的任务名称可以在 https://paperswithcode.com/tasks 查看。

3. Q: 下载中断后如何继续？
   A: 直接重新运行脚本，已下载的文件会被跳过

4. Q: 如何查看所有可用的任务名称？
   A: 访问 https://paperswithcode.com/tasks 查看所有可用的任务列表

## 贡献指南

欢迎提交 Issue 和 Pull Request 来帮助改进这个项目。

## 许可证

MIT License

## 致谢

- [Papers with Code](https://paperswithcode.com/)
- 所有论文作者和代码贡献者
