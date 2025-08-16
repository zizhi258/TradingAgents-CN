# Gemini API 服务介绍

## 服务概览

本服务提供基于 Google Gemini 模型的 API 接口，支持多种模型变体，兼容 OpenAI 格式，无需翻墙即可使用。

## 基本信息

- **API 地址**: `https://jimiround-latest.onrender.com/v1`
- **API 密钥**: `166067743`
- **格式兼容**: OpenAI API 格式
- **网络要求**: 无需翻墙，国内直连

## 可用模型

### Vertex AI 模型（推荐）

> 带有 `[v]` 前缀的模型使用 Vertex AI，具有更稳定的智能表现和更低的截断率

| 模型名称              | 描述                 | 特点                 |
| --------------------- | -------------------- | -------------------- |
| `[v]gemini-2.5-flash` | Vertex AI Flash 版本 | 快速响应，稳定性高   |
| `[v]gemini-2.5-pro`   | Vertex AI Pro 版本   | 高质量输出，低截断率 |

### AI Studio 模型

> 使用 AI Studio 接口，配备 7 个密钥轮询机制

| 模型名称           | 描述            | 特点       |
| ------------------ | --------------- | ---------- |
| `gemini-2.5-flash` | 标准 Flash 版本 | 快速响应   |
| `gemini-2.5-pro`   | 标准 Pro 版本   | 高质量输出 |

### 联网搜索模型

> 带有 `-search` 后缀的模型支持实时联网搜索功能

| 模型名称                  | 描述             | 特点                |
| ------------------------- | ---------------- | ------------------- |
| `gemini-2.5-flash-search` | Flash + 联网搜索 | 快速响应 + 实时信息 |
| `gemini-2.5-pro-search`   | Pro + 联网搜索   | 高质量 + 实时信息   |

## 使用方法

### cURL 示例

```bash
curl -X POST "https://jimiround-latest.onrender.com/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer 166067743" \
  -d '{
    "model": "[v]gemini-2.5-pro",
    "messages": [
      {
        "role": "user",
        "content": "你好，请介绍一下自己"
      }
    ],
    "temperature": 0.7,
    "max_tokens": 1000
  }'
```

### Python 示例

```python
import requests
import json

url = "https://jimiround-latest.onrender.com/v1/chat/completions"
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer 166067743"
}

data = {
    "model": "[v]gemini-2.5-pro",
    "messages": [
        {
            "role": "user",
            "content": "你好，请介绍一下自己"
        }
    ],
    "temperature": 0.7,
    "max_tokens": 1000
}

response = requests.post(url, headers=headers, json=data)
result = response.json()
print(result)
```

### JavaScript 示例

```javascript
const apiUrl = "https://jimiround-latest.onrender.com/v1/chat/completions";
const apiKey = "166067743";

async function callGeminiAPI(message, model = "[v]gemini-2.5-pro") {
  try {
    const response = await fetch(apiUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model: model,
        messages: [
          {
            role: "user",
            content: message,
          },
        ],
        temperature: 0.7,
        max_tokens: 1000,
      }),
    });

    const data = await response.json();
    return data;
  } catch (error) {
    console.error("API调用失败:", error);
  }
}

// 使用示例
callGeminiAPI("你好，请介绍一下自己").then((result) => {
  console.log(result);
});
```

## 模型选择建议

### 根据需求选择模型

1. **追求稳定性和质量**: 选择 `[v]` 前缀的 Vertex AI 模型

   - `[v]gemini-2.5-pro` - 最高质量
   - `[v]gemini-2.5-flash` - 平衡速度与质量

2. **需要实时信息**: 选择 `-search` 后缀的联网模型

   - `gemini-2.5-pro-search` - 高质量 + 联网搜索
   - `gemini-2.5-flash-search` - 快速响应 + 联网搜索

3. **一般用途**: 使用标准模型
   - `gemini-2.5-pro` - 高质量输出
   - `gemini-2.5-flash` - 快速响应

## 参数说明

| 参数          | 类型    | 描述             | 默认值 |
| ------------- | ------- | ---------------- | ------ |
| `model`       | string  | 模型名称         | 必填   |
| `messages`    | array   | 对话消息数组     | 必填   |
| `temperature` | float   | 创造性控制 (0-2) | 1.0    |
| `max_tokens`  | integer | 最大输出长度     | 无限制 |
| `top_p`       | float   | 核采样参数 (0-1) | 1.0    |
| `stream`      | boolean | 是否流式输出     | false  |

## 技术特性

- **OpenAI 格式兼容**: 可直接替换 OpenAI API
- **国内直连**: 无需 VPN 或代理
- **多密钥轮询**: AI Studio 模型使用 7 个密钥轮询，提高稳定性
- **联网搜索**: 支持实时信息获取
- **Vertex AI**: 提供更稳定的模型版本
- **流式输出**: 支持实时响应流

## 联系方式

如有问题或需要技术支持，请联系服务提供方。

---

_最后更新: 2025 年 8 月_
