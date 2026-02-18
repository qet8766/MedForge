import type { Metadata } from "next";

import { StatusDashboard } from "@/components/status/status-dashboard";

export const metadata: Metadata = {
  title: "Server Status | MedForge",
  description:
    "Real-time hardware status of the MedForge GPU server, including CPU, memory, GPU, and disk utilization.",
};

export default function StatusPage(): React.JSX.Element {
  return (
    <main className="min-h-screen bg-[#0a0a0f]">
      <StatusDashboard />
    </main>
  );
}
