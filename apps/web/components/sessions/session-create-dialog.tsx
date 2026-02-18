"use client";

import { useState } from "react";

import { Loader2, Plus } from "lucide-react";
import { toast } from "sonner";

import { apiPostJson, type SessionCreateResponse } from "@/lib/api";
import { apiPathForSurface, inferClientSurface } from "@/lib/surface";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";

type SessionCreateDialogProps = {
  onCreated?: (session: SessionCreateResponse) => void;
  disabled?: boolean;
};

export function SessionCreateDialog({
  onCreated,
  disabled = false,
}: SessionCreateDialogProps): React.JSX.Element {
  const [open, setOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const surface = inferClientSurface();

  async function handleCreate(): Promise<void> {
    setCreating(true);
    try {
      const response = await apiPostJson<SessionCreateResponse>(
        apiPathForSurface(surface, "/sessions"),
        {}
      );
      toast.success(
        `Session ${response.session.slug} created on GPU ${response.session.gpu_id}.`
      );
      setOpen(false);
      onCreated?.(response);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Session creation failed.";
      toast.error(message);
    } finally {
      setCreating(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button disabled={disabled} data-testid="session-create">
          <Plus className="size-4" />
          New Session
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create New Session</DialogTitle>
          <DialogDescription>
            Launch a new GPU-backed development session. You will be assigned an
            available GPU automatically.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3 py-2">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Surface</span>
            <Badge variant="outline">{surface.toUpperCase()}</Badge>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Pack</span>
            <span className="text-sm font-mono">default</span>
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => setOpen(false)}
            disabled={creating}
          >
            Cancel
          </Button>
          <Button onClick={handleCreate} disabled={creating}>
            {creating ? (
              <>
                <Loader2 className="size-4 animate-spin" />
                Creating...
              </>
            ) : (
              "Create Session"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
