import type { Metadata } from "next";

import { ProfileForm } from "@/components/settings/profile-form";

export const metadata: Metadata = {
  title: "Profile Settings - MedForge",
};

export default function ProfileSettingsPage(): React.JSX.Element {
  return <ProfileForm />;
}
