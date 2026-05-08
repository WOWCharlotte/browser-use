# MCP Servers 配置

## 概述

MCP (Model Context Protocol) 用于集成外部工具到 AI Coding Agent 系统中。

## 配置格式

```json
{
  "mcpServers": {
    "server-name": {
      "command": "npx",
      "args": ["-y", "@server/package"],
      "env": {
        "API_KEY": "your-api-key"
      }
    }
  }
}
```

## MCP Server 类型

### 1. 工具类 Server
提供工具调用能力：
- 文件系统操作
- Git 操作
- 数据库操作
- API 调用

### 2. 资源类 Server
提供资源访问能力：
- 文档检索
- 日志查看
- 配置查询

### 3. 提示类 Server
提供预定义提示：
- 代码审查模板
- 文档生成模板

## 内置 MCP Server 配置

### Chrome DevTools MCP
```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-server-chrome-devtools"]
    }
  }
}
```

### Puppeteer MCP
```json
{
  "mcpServers": {
    "puppeteer": {
      "command": "npx",
      "args": ["-y", "@puppeteer/mcp-server"]
    }
  }
}
```

### GitHub MCP
```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@github/github-mcp-server"],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
```

## 安全考虑

### 环境变量
- 不要在配置文件中硬编码秘钥
- 使用环境变量引用 `${VAR_NAME}`
- 确保 CI/CD 环境正确配置秘钥

### 权限控制
- 最小权限原则
- 只授予必要的工具权限
- 定期审计 Server 配置

## 故障排除

### Server 启动失败
1. 检查命令是否正确
2. 验证包是否已安装
3. 检查端口是否被占用

### 工具调用超时
1. 增加 timeout 配置
2. 检查网络连接
3. 验证 Server 状态

## 常用 Server 列表

| Server | 用途 | 官方包 |
|--------|------|--------|
| Chrome DevTools | 浏览器自动化 | @anthropic/mcp-server-chrome-devtools |
| Puppeteer | 浏览器控制 | @puppeteer/mcp-server |
| GitHub | GitHub 操作 | @github/github-mcp-server |
| Filesystem | 文件操作 | @modelcontextprotocol/server-filesystem |
| Git | Git 操作 | @modelcontextprotocol/server-git |
