import type { Metadata } from "next";

import { PageHeader } from "@/components/layout/page-header";
import { GlobalLeaderboard } from "@/components/rankings/global-leaderboard";

export const metadata: Metadata = {
  title: "Rankings - MedForge",
};

export default function RankingsPage(): React.JSX.Element {
  return (
    <div className="space-y-8">
      <PageHeader
        title="Rankings"
        description="Global leaderboard across all competitions."
      />
      <GlobalLeaderboard />
    </div>
  );
}
