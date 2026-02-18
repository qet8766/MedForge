import {
  LayoutDashboard,
  Monitor,
  Trophy,
  Database,
  Medal,
  Users,
  ShieldCheck,
} from "lucide-react"

import type { LucideIcon } from "lucide-react"

export type NavLink = {
  href: string
  label: string
  icon: LucideIcon
}

export type NavSection = {
  title: string
  links: NavLink[]
}

export const MAIN_NAV_LINKS: NavLink[] = [
  { href: "/sessions", label: "Sessions", icon: Monitor },
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
]

export const EXPLORE_NAV_LINKS: NavLink[] = [
  { href: "/competitions", label: "Competitions", icon: Trophy },
  { href: "/datasets", label: "Datasets", icon: Database },
  { href: "/rankings", label: "Rankings", icon: Medal },
]

export const ADMIN_NAV_LINKS: NavLink[] = [
  { href: "/admin/users", label: "Users", icon: Users },
  { href: "/admin/sessions", label: "Sessions", icon: Monitor },
  { href: "/admin/competitions", label: "Competitions", icon: ShieldCheck },
]

export const NAV_SECTIONS: NavSection[] = [
  { title: "Main", links: MAIN_NAV_LINKS },
  { title: "Explore", links: EXPLORE_NAV_LINKS },
]
