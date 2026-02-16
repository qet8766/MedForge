import Link from "next/link";

export function Nav(): React.JSX.Element {
  return (
    <nav>
      <div className="nav-inner">
        <strong>MedForge</strong>
        <div className="nav-links">
          <Link href="/">Home</Link>
          <Link href="/competitions">Competitions</Link>
          <Link href="/datasets">Datasets</Link>
          <Link href="/sessions">Sessions</Link>
          <Link href="/auth/login">Login</Link>
          <Link href="/auth/signup">Sign up</Link>
        </div>
      </div>
    </nav>
  );
}
