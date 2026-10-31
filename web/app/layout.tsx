import type { Metadata } from "next";
import { Shell } from "@/components/ui";
import { TrafficProvider } from "@/components/provider";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Dar Traffic · A closer look at Dar’s roads",
    template: "%s · Dar Traffic",
  },
  description:
    "Recorded traffic estimates, corridor details and history for 21 monitored corridors in Dar es Salaam.",
  icons: { icon: "/icon.svg" },
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" data-scroll-behavior="smooth">
      <body>
        <TrafficProvider>
          <Shell>{children}</Shell>
        </TrafficProvider>
      </body>
    </html>
  );
}
