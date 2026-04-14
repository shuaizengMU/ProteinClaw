# API Keys 配置面板 — 设计文档

**日期：** 2026-04-11  
**状态：** 已审批

---

## 概述

在 Sidebar 的 Settings 菜单中新增"API Keys"入口，点击后从 Sidebar 右侧滑入一个配置面板，用户可以直接编辑各 provider 的 API key，失焦自动保存到 `localStorage`。

---

## 入口

- Settings 下拉菜单新增 **"API Keys"** 菜单项（使用 `Key` 图标，来自 lucide-react）
- 位置：放在 "Appearance" 上方
- 点击后：关闭 Settings 下拉菜单，滑入 ApiKeysPanel

---

## 面板布局

### 尺寸与位置
- 宽度：**240px**，固定
- 位置：紧靠 Sidebar 右侧，与 Sidebar 等高
- 聊天区域在面板打开时向右偏移，不使用遮罩

### 头部
```
← API Keys
```
- `←` 箭头按钮，点击关闭面板（向左滑出）
- 支持 ESC 键关闭

### Provider 列表

支持的 provider 及其 localStorage key：

| Provider   | localStorage key    |
|------------|---------------------|
| Anthropic  | `ANTHROPIC_API_KEY` |
| OpenAI     | `OPENAI_API_KEY`    |
| DeepSeek   | `DEEPSEEK_API_KEY`  |
| Google     | `GEMINI_API_KEY`    |

每个 provider 块包含：
- Provider 名称（小型全大写标签）
- 一个输入字段，显示当前状态：
  - **已设置**：遮码显示，如 `sk-ant-••••••••`（前6字符可见，其余遮码）
  - **未设置**：灰色 placeholder `点击输入...`

### 编辑交互
- 点击输入字段 → 变为 `type="text"` 可编辑状态，显示明文
- `onBlur` 时自动保存：
  - 若 value 非空 → `localStorage.setItem(configKey, value.trim())`
  - 若 value 为空 → `localStorage.removeItem(configKey)`（清除 key）
- 无需任何保存/取消按钮

---

## 组件架构

### 新建文件
**`frontend/src/components/ApiKeysPanel.tsx`**
- Props：`onClose: () => void`
- 内部状态：每个 provider 的 input 值（从 localStorage 初始化）
- 完全自包含，不依赖外部状态

### 修改文件

**`frontend/src/components/Sidebar.tsx`**
- 新增 prop：`onOpenApiKeys: () => void`
- Settings 下拉菜单新增 "API Keys" 菜单项

**`frontend/src/App.tsx`**
- 新增 state：`showApiKeys: boolean`
- 将 `showApiKeys` 和 `setShowApiKeys` 传给 Sidebar 和 ApiKeysPanel
- 在布局中条件渲染 `<ApiKeysPanel>`

**样式（`frontend/src/index.css` 或 `App.css`）**
- `.api-keys-panel`：面板基础样式（宽度、背景、border）
- 滑入/滑出动画：`transform: translateX(-100%)` → `translateX(0)`，`transition: transform 250ms ease`
- 面板打开时 `.chat-window` 的 `margin-left` 或布局调整

---

## 数据流

```
localStorage (ANTHROPIC_API_KEY, etc.)
       ↕  初始化读取 / onBlur 写入
ApiKeysPanel (本地 input state)

useChat.ts → 发送消息时读取 localStorage → 传给 backend
```

面板不需要与 `useChat` 或任何 hook 通信，直接读写 localStorage 即可。

---

## 边界条件

- 面板打开时可以正常进行聊天操作（聊天区域不被遮挡）
- 面板内输入的 key 不做格式校验（后端返回错误时已有提示）
- 遮码逻辑：取前 6 个字符 + `••••••••`，若 key 长度 ≤ 6 则全部遮码

---

## 不在范围内

- Key 格式校验
- 测试 API key 是否有效的功能
- 多账户/多 key 支持
