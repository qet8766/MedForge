"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu } from "lucide-react";

import { cn } from "@/lib/utils";
import { NAV_SECTIONS, ADMIN_NAV_LINKS, type NavSection } from "@/lib/nav";
import { useAuthContext } from "@/components/providers/auth-provider";
import { BrandLogo } from "@/components/layout/brand-logo";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { Separator } from "@/components/ui/separator";

type MobileNavSectionProps = {
  section: NavSection;
  pathname: string;
  onNavigate: () => void;
};

function MobileNavSection({ section, pathname, onNavigate }: MobileNavSectionProps): React.JSX.Element {
  return (
    <div className="flex flex-col gap-0.5">
      <p className="px-3 py-1.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground/60">
        {section.title}
      </p>
      {section.links.map((link) => {
        const Icon = link.icon;
        const isActive = pathname.startsWith(link.href);
        return (
          <Link
            key={link.href}
            href={link.href}
            onClick={onNavigate}
            className={cn(
              "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
              isActive
                ? "bg-accent text-accent-foreground"
                : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
            )}
          >
            <Icon className="size-4" />
            {link.label}
          </Link>
        );
      })}
    </div>
  );
}

export function MobileMenu(): React.JSX.Element {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const { user } = useAuthContext();

  const isAdmin = user?.role === "admin";

  function handleNavigate(): void {
    setOpen(false);
  }

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button variant="ghost" size="icon-sm">
          <Menu className="size-5" />
          <span className="sr-only">Open menu</span>
        </Button>
      </SheetTrigger>
      <SheetContent side="left" className="w-64">
        <SheetHeader>
          <SheetTitle>
            <BrandLogo />
          </SheetTitle>
        </SheetHeader>
        <nav className="flex flex-col gap-3 px-2 pt-4">
          {NAV_SECTIONS.map((section) => (
            <MobileNavSection
              key={section.title}
              section={section}
              pathname={pathname}
              onNavigate={handleNavigate}
            />
          ))}

          {isAdmin && (
            <>
              <Separator />
              <MobileNavSection
                section={{ title: "Admin", links: ADMIN_NAV_LINKS }}
                pathname={pathname}
                onNavigate={handleNavigate}
              />
            </>
          )}
        </nav>
      </SheetContent>
    </Sheet>
  );
}
