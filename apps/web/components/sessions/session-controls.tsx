import { Button } from "@/components/ui/button";

type SessionControlsProps = {
  surfaceLabel: string;
  hasSession: boolean;
  onCreateSession: () => void;
  onStopSession: () => void;
  onWhoAmI: () => void;
  onLogout: () => void;
};

export function SessionControls({
  surfaceLabel,
  hasSession,
  onCreateSession,
  onStopSession,
  onWhoAmI,
  onLogout,
}: SessionControlsProps): React.JSX.Element {
  return (
    <div className="flex flex-wrap gap-3">
      <Button onClick={onCreateSession} data-testid="session-create">
        Create {surfaceLabel} Session
      </Button>
      <Button
        variant="outline"
        onClick={onStopSession}
        disabled={!hasSession}
        data-testid="session-stop"
      >
        Stop Current Session
      </Button>
      <Button variant="secondary" onClick={onWhoAmI} data-testid="session-whoami">
        Check /api/v2/me
      </Button>
      <Button variant="ghost" onClick={onLogout} data-testid="session-logout">
        Sign out
      </Button>
    </div>
  );
}
