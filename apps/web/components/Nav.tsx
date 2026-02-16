"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";

const links = [
  { href: "/", label: "Home" },
  { href: "/competitions", label: "Competitions" },
  { href: "/datasets", label: "Datasets" },
  { href: "/sessions", label: "Sessions" },
] as const;

function NavLink({ href, label, pathname }: { href: string; label: string; pathname: string }): React.JSX.Element {
  const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
  return (
    <Link
      href={href}
      className={cn(
        "text-sm font-medium transition-colors hover:text-primary",
        active ? "text-primary" : "text-muted-foreground"
      )}
    >
      {label}
    </Link>
  );
}

export function Nav(): React.JSX.Element {
  const pathname = usePathname();

  return (
    <nav className="border-b border-border bg-card/50 backdrop-blur-sm">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-3">
        <Link href="/" className="text-lg font-bold tracking-tight text-foreground">
          MedForge
        </Link>

        {/* Desktop links */}
        <div className="hidden items-center gap-6 md:flex">
          {links.map((link) => (
            <NavLink key={link.href} href={link.href} label={link.label} pathname={pathname} />
          ))}
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" asChild>
              <Link href="/auth/login">Login</Link>
            </Button>
            <Button size="sm" asChild>
              <Link href="/auth/signup">Sign up</Link>
            </Button>
          </div>
        </div>

        {/* Mobile menu */}
        <Sheet>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon" className="md:hidden">
              <Menu className="size-5" />
              <span className="sr-only">Menu</span>
            </Button>
          </SheetTrigger>
          <SheetContent side="right">
            <SheetHeader>
              <SheetTitle>MedForge</SheetTitle>
            </SheetHeader>
            <div className="flex flex-col gap-4 px-4">
              {links.map((link) => (
                <NavLink key={link.href} href={link.href} label={link.label} pathname={pathname} />
              ))}
              <div className="flex flex-col gap-2 border-t border-border pt-4">
                <Button variant="ghost" size="sm" asChild>
                  <Link href="/auth/login">Login</Link>
                </Button>
                <Button size="sm" asChild>
                  <Link href="/auth/signup">Sign up</Link>
                </Button>
              </div>
            </div>
          </SheetContent>
        </Sheet>
      </div>
    </nav>
  );
}
