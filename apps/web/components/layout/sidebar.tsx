"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronDown, PanelLeftClose, PanelLeftOpen } from "lucide-react";

import { cn } from "@/lib/utils";
import { NAV_SECTIONS, ADMIN_NAV_LINKS, type NavLink, type NavSection } from "@/lib/nav";
import { useSidebarState } from "@/lib/hooks/use-sidebar-state";
import { useAuthContext } from "@/components/providers/auth-provider";
import { BrandLogo } from "@/components/layout/brand-logo";
import { SessionIndicator } from "@/components/layout/session-indicator";
import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

type SidebarNavLinkProps = {
  link: NavLink;
  isActive: boolean;
  collapsed: boolean;
};

function SidebarNavLink({ link, isActive, collapsed }: SidebarNavLinkProps): React.JSX.Element {
  const Icon = link.icon;

  return (
    <Link
      href={link.href}
      title={collapsed ? link.label : undefined}
      className={cn(
        "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
        isActive
          ? "bg-sidebar-accent text-sidebar-accent-foreground"
          : "text-sidebar-foreground/60 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
        collapsed && "justify-center px-0"
      )}
    >
      <Icon className="size-4 shrink-0" />
      {!collapsed && <span>{link.label}</span>}
    </Link>
  );
}

type SidebarSectionProps = {
  section: NavSection;
  pathname: string;
  collapsed: boolean;
};

function SidebarSection({ section, pathname, collapsed }: SidebarSectionProps): React.JSX.Element {
  if (collapsed) {
    return (
      <div className="flex flex-col gap-1">
        {section.links.map((link) => (
          <SidebarNavLink
            key={link.href}
            link={link}
            isActive={pathname.startsWith(link.href)}
            collapsed
          />
        ))}
      </div>
    );
  }

  return (
    <Collapsible defaultOpen>
      <CollapsibleTrigger className="flex w-full items-center justify-between px-3 py-1.5 text-xs font-semibold uppercase tracking-wider text-sidebar-foreground/40 hover:text-sidebar-foreground/60">
        {section.title}
        <ChevronDown className="size-3 transition-transform [[data-state=closed]>&]:rotate-[-90deg]" />
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="flex flex-col gap-0.5">
          {section.links.map((link) => (
            <SidebarNavLink
              key={link.href}
              link={link}
              isActive={pathname.startsWith(link.href)}
              collapsed={false}
            />
          ))}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}

export function Sidebar(): React.JSX.Element {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useSidebarState();
  const { user } = useAuthContext();

  const isAdmin = user?.role === "admin";

  return (
    <aside
      className={cn(
        "hidden flex-col border-r bg-sidebar transition-[width] duration-200 md:flex",
        collapsed ? "w-16" : "w-56"
      )}
    >
      <div className={cn(
        "flex h-14 items-center border-b px-3",
        collapsed ? "justify-center" : "justify-between"
      )}>
        {!collapsed && <BrandLogo className="text-base" />}
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={() => setCollapsed(!collapsed)}
        >
          {collapsed ? (
            <PanelLeftOpen className="size-4" />
          ) : (
            <PanelLeftClose className="size-4" />
          )}
          <span className="sr-only">{collapsed ? "Expand" : "Collapse"} sidebar</span>
        </Button>
      </div>

      <SessionIndicator collapsed={collapsed} />

      <nav className="flex flex-1 flex-col gap-3 overflow-y-auto p-2">
        {NAV_SECTIONS.map((section) => (
          <SidebarSection
            key={section.title}
            section={section}
            pathname={pathname}
            collapsed={collapsed}
          />
        ))}

        {isAdmin && (
          <SidebarSection
            section={{ title: "Admin", links: ADMIN_NAV_LINKS }}
            pathname={pathname}
            collapsed={collapsed}
          />
        )}
      </nav>
    </aside>
  );
}
