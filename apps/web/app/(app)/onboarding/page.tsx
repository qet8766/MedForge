import type { Metadata } from "next";

import { OnboardingWizard } from "@/components/onboarding/onboarding-wizard";

export const metadata: Metadata = {
  title: "Onboarding - MedForge",
};

export default function OnboardingPage(): React.JSX.Element {
  return <OnboardingWizard />;
}
