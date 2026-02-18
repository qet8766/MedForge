"use client";

import { Square } from "lucide-react";

import { isTransitioning } from "@/lib/status";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { SessionCreateDialog } from "@/components/sessions/session-create-dialog";
import type { SessionCreateResponse } from "@/lib/contracts";

type SessionControlsProps = {
  hasActiveSession: boolean;
  activeSessionSlug: string | null;
  activeSessionStatus: string | null;
  onStopSession: () => Promise<void>;
  onSessionCreated?: (response: SessionCreateResponse) => void;
};

export function SessionControls({
  hasActiveSession,
  activeSessionSlug,
  activeSessionStatus,
  onStopSession,
  onSessionCreated,
}: SessionControlsProps): React.JSX.Element {
  const transitioning = activeSessionStatus
    ? isTransitioning(activeSessionStatus)
    : false;

  return (
    <div className="flex flex-wrap gap-3">
      <SessionCreateDialog
        onCreated={onSessionCreated}
        disabled={hasActiveSession}
      />

      {hasActiveSession ? (
        <ConfirmDialog
          title="Stop Session"
          description={`This will stop session ${activeSessionSlug ?? "current"}. Any unsaved work in the IDE may be lost.`}
          confirmLabel="Stop Session"
          onConfirm={onStopSession}
          trigger={
            <Button
              variant="destructive"
              disabled={transitioning}
              data-testid="session-stop"
            >
              <Square className="size-4" />
              Stop Session
            </Button>
          }
        />
      ) : null}
    </div>
  );
}
