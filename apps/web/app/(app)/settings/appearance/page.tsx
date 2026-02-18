import type { Metadata } from "next";

import { AppearanceForm } from "@/components/settings/appearance-form";

export const metadata: Metadata = {
  title: "Appearance Settings - MedForge",
};

export default function AppearanceSettingsPage(): React.JSX.Element {
  return <AppearanceForm />;
}
