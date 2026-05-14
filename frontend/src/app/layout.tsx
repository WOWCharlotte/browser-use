import "./globals.css";
import "@copilotkit/react-core/v2/styles.css";
import { CopilotKit } from "@copilotkit/react-core";

export const metadata = {
  title: "AI Workspace",
  description: "AI Workspace with real Chrome browser",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <CopilotKit runtimeUrl="/api/copilotkit" agent="default">
          {children}
        </CopilotKit>
      </body>
    </html>
  );
}