import { PageHeader } from "@/components/layout/page-header";
import { SettingsNav } from "@/components/settings/settings-nav";

export default function SettingsLayout({ children }: { children: React.ReactNode }): React.JSX.Element {
  return (
    <div className="space-y-6">
      <PageHeader title="Settings" description="Manage your account settings and preferences." />
      <SettingsNav />
      {children}
    </div>
  );
}
