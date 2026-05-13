# CopilotKitProvider 集成说明

## 集成步骤

由于当前 frontend 项目结构中未找到 `app/layout.tsx`，需要手动添加集成步骤：

### 1. 创建或修改 `frontend/src/app/layout.tsx`

```tsx
import { CopilotKitProvider } from "@/components/CopilotKitProvider";

export default function RootLayout({
	children,
}: {
	children: React.ReactNode;
}) {
	return (
		<html lang="zh-CN">
			<body>
				<CopilotKitProvider>{children}</CopilotKitProvider>
			{/* 其他 providers */}
			{/* 其他 layout 内容 */}
			</body>
		</html>
	);
}
```

### 2. 验证集成

确保：
- `CopilotKitProvider` 包裹整个 App
- `runtimeUrl` 指向 `/api/copilotkit`
- `agent` 属性配置正确

### 3. 环境变量配置

在 `frontend/.env.local` 中添加：

```env
NEXT_PUBLIC_AGENT_URL=http://localhost:8888/api/agui
```

## 注意事项

- 如果已有 `layout.tsx`，只需在 body 中添加 `CopilotKitProvider`
- 不要在同一个 App 中使用多个 `CopilotKitProvider`
- `runtimeUrl` 应为绝对 URL 或相对于域名的路径