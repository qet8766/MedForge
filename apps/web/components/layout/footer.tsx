export function Footer(): React.JSX.Element {
  return (
    <footer className="border-t py-6">
      <div className="mx-auto max-w-7xl px-6">
        <p className="text-muted-foreground text-sm">
          MedForge &middot; {new Date().getFullYear()}
        </p>
      </div>
    </footer>
  );
}
