export default function AuthLayout({ children }: { children: React.ReactNode }): React.JSX.Element {
  return (
    <div className="flex min-h-[calc(100vh-3.5rem)] items-center justify-center bg-background">
      {children}
    </div>
  );
}
