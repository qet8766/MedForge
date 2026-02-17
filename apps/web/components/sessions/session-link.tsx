type SessionLinkProps = {
  slug: string;
  domain: string;
  children?: React.ReactNode;
};

export function SessionLink({ slug, domain, children }: SessionLinkProps): React.JSX.Element {
  const href = `https://${slug}.medforge.${domain}`;

  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1.5 text-sm font-medium text-primary underline-offset-4 hover:underline"
    >
      {children ?? href}
    </a>
  );
}
