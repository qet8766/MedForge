"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowRight, Check, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StepIndicator } from "@/components/onboarding/step-indicator";

const INTEREST_OPTIONS = [
  { id: "medical-imaging", label: "Medical Imaging" },
  { id: "nlp", label: "NLP" },
  { id: "genomics", label: "Genomics" },
  { id: "drug-discovery", label: "Drug Discovery" },
] as const;

const TOTAL_STEPS = 3;

function WelcomeStep({ onNext }: { onNext: () => void }): React.JSX.Element {
  return (
    <div className="flex flex-col items-center gap-6 text-center">
      <div className="flex size-16 items-center justify-center rounded-full bg-primary/10">
        <Sparkles className="size-8 text-primary" />
      </div>
      <div className="space-y-2">
        <h2 className="text-3xl font-bold tracking-tight">Welcome to MedForge</h2>
        <p className="text-muted-foreground max-w-md">
          A GPU-powered platform for medical research competitions, datasets, and
          collaborative development environments.
        </p>
      </div>
      <Button size="lg" onClick={onNext}>
        Get Started
        <ArrowRight className="size-4" />
      </Button>
    </div>
  );
}

function InterestsStep({
  selected,
  onToggle,
  onNext,
}: {
  selected: Set<string>;
  onToggle: (id: string) => void;
  onNext: () => void;
}): React.JSX.Element {
  return (
    <div className="flex flex-col items-center gap-6 text-center">
      <div className="space-y-2">
        <h2 className="text-2xl font-bold tracking-tight">Pick Your Interests</h2>
        <p className="text-muted-foreground">
          Select areas you are most interested in to personalize your experience.
        </p>
      </div>
      <div className="grid w-full max-w-sm grid-cols-1 gap-3">
        {INTEREST_OPTIONS.map((option) => {
          const isSelected = selected.has(option.id);
          return (
            <button
              key={option.id}
              type="button"
              onClick={() => onToggle(option.id)}
              className={
                "flex items-center justify-between rounded-lg border px-4 py-3 text-sm font-medium transition-colors " +
                (isSelected
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-border text-foreground hover:bg-accent")
              }
            >
              {option.label}
              {isSelected ? <Check className="size-4" /> : null}
            </button>
          );
        })}
      </div>
      <Button size="lg" onClick={onNext}>
        Continue
        <ArrowRight className="size-4" />
      </Button>
    </div>
  );
}

function CompleteStep(): React.JSX.Element {
  return (
    <div className="flex flex-col items-center gap-6 text-center">
      <div className="flex size-16 items-center justify-center rounded-full bg-primary/10">
        <Check className="size-8 text-primary" />
      </div>
      <div className="space-y-2">
        <h2 className="text-3xl font-bold tracking-tight">You're All Set!</h2>
        <p className="text-muted-foreground max-w-md">
          Your account is ready. Head to the dashboard to explore competitions,
          datasets, and GPU sessions.
        </p>
      </div>
      <Button size="lg" asChild>
        <Link href="/dashboard">
          Go to Dashboard
          <ArrowRight className="size-4" />
        </Link>
      </Button>
    </div>
  );
}

export function OnboardingWizard(): React.JSX.Element {
  const [step, setStep] = useState(0);
  const [interests, setInterests] = useState<Set<string>>(new Set());

  function handleToggleInterest(id: string): void {
    setInterests((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

  function handleNext(): void {
    setStep((prev) => Math.min(prev + 1, TOTAL_STEPS - 1));
  }

  return (
    <Card className="w-full max-w-lg">
      <CardHeader className="items-center">
        <CardTitle className="sr-only">Onboarding</CardTitle>
        <StepIndicator currentStep={step} totalSteps={TOTAL_STEPS} />
      </CardHeader>
      <CardContent className="flex flex-col items-center pb-10">
        {step === 0 && <WelcomeStep onNext={handleNext} />}
        {step === 1 && (
          <InterestsStep
            selected={interests}
            onToggle={handleToggleInterest}
            onNext={handleNext}
          />
        )}
        {step === 2 && <CompleteStep />}
      </CardContent>
    </Card>
  );
}
