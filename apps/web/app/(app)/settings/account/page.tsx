import type { Metadata } from "next";

import { AccountForm } from "@/components/settings/account-form";

export const metadata: Metadata = {
  title: "Account Settings - MedForge",
};

export default function AccountSettingsPage(): React.JSX.Element {
  return <AccountForm />;
}
