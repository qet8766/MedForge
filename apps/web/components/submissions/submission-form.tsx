"use client";

import { useCallback, useRef, useState } from "react";
import { Upload } from "lucide-react";

import { apiSubmitFile } from "@/lib/api";
import { apiPathForSurface, inferClientSurface } from "@/lib/surface";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";

interface SubmissionFormProps {
  slug: string;
  onResult: (result: string) => void;
  onError: (error: string) => void;
}

export function SubmissionForm({ slug, onResult, onError }: SubmissionFormProps): React.JSX.Element {
  const [file, setFile] = useState<File | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [progress, setProgress] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const surface = inferClientSurface();

  function validateAndSetFile(candidate: File | undefined): void {
    if (!candidate) return;
    if (!candidate.name.endsWith(".csv")) {
      onError("Only .csv files are accepted.");
      return;
    }
    onError("");
    onResult("");
    setFile(candidate);
  }

  function handleDragOver(event: React.DragEvent<HTMLDivElement>): void {
    event.preventDefault();
    event.stopPropagation();
    setIsDragOver(true);
  }

  function handleDragLeave(event: React.DragEvent<HTMLDivElement>): void {
    event.preventDefault();
    event.stopPropagation();
    setIsDragOver(false);
  }

  function handleDrop(event: React.DragEvent<HTMLDivElement>): void {
    event.preventDefault();
    event.stopPropagation();
    setIsDragOver(false);
    const droppedFile = event.dataTransfer.files[0];
    validateAndSetFile(droppedFile);
  }

  function handleFileChange(event: React.ChangeEvent<HTMLInputElement>): void {
    const selectedFile = event.target.files?.[0];
    validateAndSetFile(selectedFile);
  }

  function handleZoneClick(): void {
    fileInputRef.current?.click();
  }

  const handleZoneKeyDown = useCallback((event: React.KeyboardEvent<HTMLDivElement>): void => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      fileInputRef.current?.click();
    }
  }, []);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    onError("");
    onResult("");

    if (!file) {
      onError("Choose a CSV file first.");
      return;
    }

    setIsSubmitting(true);
    setProgress(20);

    try {
      const progressInterval = setInterval(() => {
        setProgress((prev) => Math.min(prev + 10, 90));
      }, 300);

      const payload = await apiSubmitFile(
        apiPathForSurface(surface, `/competitions/${slug}/submissions`),
        file,
      );

      clearInterval(progressInterval);
      setProgress(100);
      onResult(JSON.stringify(payload, null, 2));
    } catch (submitError) {
      onError(submitError instanceof Error ? submitError.message : "Submission failed");
    } finally {
      setIsSubmitting(false);
      setProgress(0);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div
        role="button"
        tabIndex={0}
        onClick={handleZoneClick}
        onKeyDown={handleZoneKeyDown}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center gap-4 rounded-lg border-2 border-dashed px-6 py-12 text-center transition-colors",
          isDragOver
            ? "border-primary bg-primary/5"
            : "border-muted-foreground/25 hover:border-muted-foreground/50",
        )}
      >
        <div
          className={cn(
            "flex size-14 items-center justify-center rounded-full transition-colors",
            isDragOver ? "bg-primary/10" : "bg-muted",
          )}
        >
          <Upload
            className={cn(
              "size-6 transition-colors",
              isDragOver ? "text-primary" : "text-muted-foreground",
            )}
          />
        </div>

        {file ? (
          <div className="space-y-1">
            <p className="text-sm font-medium">{file.name}</p>
            <p className="text-xs text-muted-foreground">
              {(file.size / 1024).toFixed(1)} KB — click or drop to replace
            </p>
          </div>
        ) : (
          <div className="space-y-1">
            <p className="text-sm font-medium">Drop your CSV file here</p>
            <p className="text-xs text-muted-foreground">or click to browse — .csv files only</p>
          </div>
        )}

        <input
          ref={fileInputRef}
          type="file"
          accept=".csv"
          onChange={handleFileChange}
          className="hidden"
          aria-label="Upload CSV file"
        />
      </div>

      {isSubmitting ? (
        <div className="space-y-2">
          <Progress value={progress} className="h-2" />
          <p className="text-center text-xs text-muted-foreground">Uploading and scoring...</p>
        </div>
      ) : null}

      <Button type="submit" disabled={!file || isSubmitting} className="w-full">
        {isSubmitting ? "Submitting..." : "Submit"}
      </Button>
    </form>
  );
}
