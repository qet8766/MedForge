"use client";

import { CheckCircle2, Circle, AlertCircle, Loader2 } from "lucide-react";

import type { SessionRead, SessionStatus } from "@/lib/contracts";
import { cn } from "@/lib/utils";
import { formatTimestamp, formatRelativeTime } from "@/lib/format";

type TimelineStep = {
  label: string;
  status: "completed" | "active" | "pending" | "error";
  timestamp: string | null;
};

function buildTimelineSteps(session: SessionRead): TimelineStep[] {
  const steps: TimelineStep[] = [];

  // Step 1: Created
  steps.push({
    label: "Created",
    status: "completed",
    timestamp: session.created_at,
  });

  // Step 2: Starting
  const startingStatus = resolveStepStatus(session.status, "starting", [
    "running",
    "stopping",
    "stopped",
  ]);
  steps.push({
    label: "Starting",
    status: startingStatus,
    timestamp: null,
  });

  // Step 3: Running
  const runningStatus = resolveStepStatus(session.status, "running", [
    "stopping",
    "stopped",
  ]);
  steps.push({
    label: "Running",
    status: runningStatus,
    timestamp: session.started_at,
  });

  // Step 4: Stopped or Error
  if (session.status === "error") {
    steps.push({
      label: "Error",
      status: "error",
      timestamp: session.stopped_at,
    });
  } else {
    const stoppedStatus = resolveStepStatus(session.status, "stopping", [
      "stopped",
    ]);
    const finalStatus =
      session.status === "stopped" ? "completed" : stoppedStatus;
    steps.push({
      label: "Stopped",
      status: finalStatus,
      timestamp: session.stopped_at,
    });
  }

  return steps;
}

function resolveStepStatus(
  sessionStatus: SessionStatus,
  activeWhen: SessionStatus,
  completedWhen: SessionStatus[]
): "completed" | "active" | "pending" | "error" {
  if (sessionStatus === activeWhen) return "active";
  if (completedWhen.includes(sessionStatus)) return "completed";
  if (sessionStatus === "error") return "error";
  return "pending";
}

function StepIcon({
  status,
}: {
  status: TimelineStep["status"];
}): React.JSX.Element {
  switch (status) {
    case "completed":
      return <CheckCircle2 className="size-5 text-primary" />;
    case "active":
      return <Loader2 className="size-5 animate-spin text-primary" />;
    case "error":
      return <AlertCircle className="size-5 text-destructive" />;
    case "pending":
      return <Circle className="size-5 text-muted-foreground/40" />;
  }
}

type SessionTimelineProps = {
  session: SessionRead;
  className?: string;
};

export function SessionTimeline({
  session,
  className,
}: SessionTimelineProps): React.JSX.Element {
  const steps = buildTimelineSteps(session);

  return (
    <div className={cn("space-y-0", className)}>
      {steps.map((step, index) => {
        const isLast = index === steps.length - 1;

        return (
          <div key={step.label} className="flex gap-3">
            <div className="flex flex-col items-center">
              <StepIcon status={step.status} />
              {!isLast ? (
                <div
                  className={cn(
                    "mt-1 w-px flex-1 min-h-6",
                    step.status === "completed"
                      ? "bg-primary/40"
                      : "bg-muted-foreground/20"
                  )}
                />
              ) : null}
            </div>
            <div className={cn("pb-4", isLast && "pb-0")}>
              <p
                className={cn(
                  "text-sm font-medium leading-5",
                  step.status === "pending" && "text-muted-foreground/50",
                  step.status === "error" && "text-destructive"
                )}
              >
                {step.label}
              </p>
              {step.timestamp ? (
                <p
                  className="text-xs text-muted-foreground"
                  title={formatTimestamp(step.timestamp)}
                >
                  {formatRelativeTime(step.timestamp)}
                </p>
              ) : null}
            </div>
          </div>
        );
      })}
    </div>
  );
}
