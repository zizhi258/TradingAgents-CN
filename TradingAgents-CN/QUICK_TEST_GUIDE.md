# 🚀 快速测试指南

## ✅ 重要说明：Python 启动完全可以测试 UI 显示效果！

**Streamlit 是纯 Web 应用，Python 直接启动的界面与 Docker 部署完全相同**

- 所有 UI 修复（下拉框、输入框、按钮、CSS 样式）都会正常显示
- 可以完整测试前端交互功能和视觉效果
- 无需 Docker 即可验证所有 UI 问题是否已修复

## 快速启动方法（推荐）

### 方法 1: 直接 Python 启动（最快，UI 效果完全相同）

```bash
# 进入项目目录
cd TradingAgents-CN

# 直接启动Web应用（无需Docker）
python start_web.py

# 然后在浏览器打开: http://localhost:8501
```

### 方法 2: 使用已有容器（如果之前构建过）

```bash
# 启动已有容器（不重新构建）
docker-compose up -d

# 查看容器状态
docker-compose ps

# 查看日志
docker-compose logs -f web
```

### 方法 3: 仅重启 Web 服务

```bash
# 仅重启web服务容器
docker-compose restart web

# 或者停止并启动特定服务
docker-compose stop web
docker-compose up -d web
```

## 开发模式快速测试

### 本地开发环境

```bash
# 安装依赖（如果还没安装）
pip install streamlit plotly

# 直接运行Streamlit
streamlit run web/app.py --server.port 8501
```

### 热重载开发

```bash
# 启用文件监控的开发模式
streamlit run web/app.py --server.fileWatcherType poll
```

## 测试重点

### 1. UI 组件测试

- ✅ 检查选择框是否正常显示选中值
- ✅ 验证输入框是否有重叠问题
- ✅ 确认按钮是否正常工作
- ✅ 测试表单提交功能

### 2. 页面功能测试

- 📋 分析配置页面
- 🤖 多模型协作页面
- ⚙️ 模型选择面板

### 3. UI 显示效果验证步骤（Python 启动即可完整测试）

1. **启动应用**: `python start_web.py`
2. **打开浏览器**: 访问 `http://localhost:8501`
3. **验证 UI 修复效果**:
   - ✅ 下拉框是否显示选中值（之前显示异常）
   - ✅ 输入框是否有重叠问题（之前重叠）
   - ✅ 按钮样式是否统一美观
   - ✅ 表单是否有提交按钮（之前缺失）
   - ✅ CSS 样式是否正确应用
4. **功能交互测试**:
   - 选择不同的市场类型和股票代码
   - 测试模型选择面板的下拉框
   - 验证表单提交功能
   - 检查页面响应式布局

### 4. 重点测试页面

- **📋 分析配置页面**: 测试表单组件和布局
- **🤖 多模型协作页面**: 验证智能体选择界面
- **⚙️ 模型选择面板**: 检查下拉框显示效果

## 故障排除

### 如果遇到依赖问题

```bash
# 安装核心依赖
pip install streamlit>=1.28.0
pip install plotly>=5.0.0
pip install pandas>=2.0.0
```

### 如果遇到端口占用

```bash
# 使用不同端口启动
streamlit run web/app.py --server.port 8502
```

### 如果需要清理 Docker 缓存

```bash
# 清理未使用的镜像和容器
docker system prune -f

# 重新构建（仅在必要时使用）
docker-compose build --no-cache web
```

## 性能优化建议

### Docker 构建优化

1. 使用 `.dockerignore` 排除不必要文件
2. 利用 Docker 层缓存
3. 仅在代码变更时重新构建

### 开发效率提升

1. 优先使用本地 Python 环境测试
2. 使用 Docker 仅用于生产环境验证
3. 利用 Streamlit 的热重载功能

## UI 修复效果验证清单

### 核心 UI 问题修复验证

- [ ] **下拉框显示修复**: 选择框能正确显示选中的值（之前显示异常）
- [ ] **输入框重叠修复**: 输入框之间没有重叠现象
- [ ] **按钮显示修复**: 表单有提交按钮且样式统一（之前缺失）
- [ ] **CSS 样式统一**: 所有组件使用一致的视觉风格

### 功能完整性验证

- [ ] 页面正常加载，无"NoneType"错误提示
- [ ] 选择框交互正常，能正确选择和显示
- [ ] 表单提交功能正常工作
- [ ] 响应式布局在不同屏幕尺寸下正常

### 视觉效果验证

- [ ] 组件间距和对齐正确
- [ ] hover 和 focus 状态有视觉反馈
- [ ] 颜色主题一致（蓝色系 #3b82f6）
- [ ] 圆角、阴影等细节样式正确应用

**✅ 确认：这些 UI 效果在 Python 直接启动和 Docker 部署中完全相同！**

## 联系支持

如果遇到问题，请检查：

1. Python 版本是否为 3.10+
2. 依赖包是否正确安装
3. 端口是否被占用
4. 浏览器控制台是否有错误信息
