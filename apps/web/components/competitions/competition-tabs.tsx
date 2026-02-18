"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

type Tab = {
  label: string;
  href: string;
};

type CompetitionTabsProps = {
  slug: string;
};

function buildTabs(slug: string): Tab[] {
  const base = `/competitions/${slug}`;
  return [
    { label: "Overview", href: base },
    { label: "Leaderboard", href: `${base}/leaderboard` },
    { label: "Submit", href: `${base}/submit` },
    { label: "History", href: `${base}/history` },
  ];
}

function isActiveTab(pathname: string, href: string, isOverview: boolean): boolean {
  if (isOverview) {
    return pathname === href;
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function CompetitionTabs({ slug }: CompetitionTabsProps): React.JSX.Element {
  const pathname = usePathname();
  const tabs = buildTabs(slug);

  return (
    <nav className="flex gap-1 border-b" aria-label="Competition sections">
      {tabs.map((tab) => {
        const isOverview = tab.href === `/competitions/${slug}`;
        const active = isActiveTab(pathname, tab.href, isOverview);

        return (
          <Link
            key={tab.href}
            href={tab.href}
            className={cn(
              "relative px-4 py-2.5 text-sm font-medium transition-colors",
              active
                ? "text-foreground"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {tab.label}
            {active ? (
              <span className="absolute inset-x-0 -bottom-px h-0.5 bg-primary" />
            ) : null}
          </Link>
        );
      })}
    </nav>
  );
}
