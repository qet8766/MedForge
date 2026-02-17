import Link from "next/link";

import { cn } from "@/lib/utils";

interface BrandLogoProps {
  className?: string;
}

export function BrandLogo({ className }: BrandLogoProps): React.JSX.Element {
  return (
    <Link href="/" className={cn("flex items-center gap-1 font-bold text-xl tracking-tight", className)}>
      <span className="text-primary">Med</span>
      <span className="text-foreground">Forge</span>
    </Link>
  );
}
