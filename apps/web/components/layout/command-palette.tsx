"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useTheme } from "next-themes";
import { Moon, Plus, Search, Sun } from "lucide-react";

import {
  MAIN_NAV_LINKS,
  EXPLORE_NAV_LINKS,
  ADMIN_NAV_LINKS,
  type NavLink,
} from "@/lib/nav";
import { useAuthContext } from "@/components/providers/auth-provider";
import { Button } from "@/components/ui/button";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";

export function CommandPalette(): React.JSX.Element {
  const [open, setOpen] = useState(false);
  const router = useRouter();
  const { setTheme, resolvedTheme } = useTheme();
  const { user } = useAuthContext();

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent): void {
      if (event.key === "k" && (event.metaKey || event.ctrlKey)) {
        event.preventDefault();
        setOpen((prev) => !prev);
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  const navigateTo = useCallback(
    (href: string) => {
      setOpen(false);
      router.push(href);
    },
    [router]
  );

  function renderNavItems(links: NavLink[]): React.JSX.Element[] {
    return links.map((link) => {
      const Icon = link.icon;
      return (
        <CommandItem
          key={link.href}
          onSelect={() => navigateTo(link.href)}
        >
          <Icon className="size-4" />
          {link.label}
        </CommandItem>
      );
    });
  }

  function handleToggleTheme(): void {
    setTheme(resolvedTheme === "dark" ? "light" : "dark");
    setOpen(false);
  }

  const isAdmin = user?.role === "admin";

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        className="hidden gap-2 text-muted-foreground md:flex"
        onClick={() => setOpen(true)}
      >
        <Search className="size-3.5" />
        <span className="text-xs">Search...</span>
        <kbd className="pointer-events-none ml-2 hidden select-none rounded border bg-muted px-1.5 py-0.5 font-mono text-[10px] font-medium sm:inline-flex">
          <span className="text-xs">&#8984;</span>K
        </kbd>
      </Button>

      <Button
        variant="ghost"
        size="icon-sm"
        className="md:hidden"
        onClick={() => setOpen(true)}
      >
        <Search className="size-4" />
        <span className="sr-only">Search</span>
      </Button>

      <CommandDialog
        open={open}
        onOpenChange={setOpen}
        title="Command Palette"
        description="Search for pages and actions"
      >
        <CommandInput placeholder="Type a command or search..." />
        <CommandList>
          <CommandEmpty>No results found.</CommandEmpty>

          <CommandGroup heading="Main">
            {renderNavItems(MAIN_NAV_LINKS)}
          </CommandGroup>

          <CommandSeparator />

          <CommandGroup heading="Explore">
            {renderNavItems(EXPLORE_NAV_LINKS)}
          </CommandGroup>

          {isAdmin && (
            <>
              <CommandSeparator />
              <CommandGroup heading="Admin">
                {renderNavItems(ADMIN_NAV_LINKS)}
              </CommandGroup>
            </>
          )}

          <CommandSeparator />

          <CommandGroup heading="Actions">
            <CommandItem onSelect={() => navigateTo("/sessions")}>
              <Plus className="size-4" />
              Create Session
            </CommandItem>
            <CommandItem onSelect={handleToggleTheme}>
              {resolvedTheme === "dark" ? (
                <Sun className="size-4" />
              ) : (
                <Moon className="size-4" />
              )}
              Toggle Theme
            </CommandItem>
          </CommandGroup>
        </CommandList>
      </CommandDialog>
    </>
  );
}
