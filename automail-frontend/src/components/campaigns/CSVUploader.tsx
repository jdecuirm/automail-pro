import { useRef, useState } from "react";
import { Upload, FileText, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { fileSize } from "@/lib/format";

interface CSVUploaderProps {
  onFile: (file: File) => void;
  onClear: () => void;
  file: File | null;
  error: string | null;
  disabled?: boolean;
}

export default function CSVUploader({
  onFile,
  onClear,
  file,
  error,
  disabled = false,
}: CSVUploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  function handleDragOver(e: React.DragEvent) {
    e.preventDefault();
    if (!disabled) setIsDragging(true);
  }

  function handleDragLeave() {
    setIsDragging(false);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setIsDragging(false);
    if (disabled) return;
    const dropped = e.dataTransfer.files[0];
    if (dropped) onFile(dropped);
  }

  function handleInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    const selected = e.target.files?.[0];
    if (selected) onFile(selected);
    // Reset input so same file can be re-selected
    e.target.value = "";
  }

  if (file) {
    return (
      <div className="flex items-center justify-between rounded-lg border bg-muted/40 px-4 py-3">
        <div className="flex items-center gap-3 min-w-0">
          <FileText className="h-5 w-5 shrink-0 text-primary" />
          <div className="min-w-0">
            <p className="truncate text-sm font-medium">{file.name}</p>
            <p className="text-xs text-muted-foreground">
              {fileSize(file.size)}
            </p>
          </div>
        </div>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          onClick={onClear}
          disabled={disabled}
          aria-label="Remove file"
          className="shrink-0 ml-2"
        >
          <X className="h-4 w-4" />
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <button
        type="button"
        disabled={disabled}
        onClick={() => inputRef.current?.click()}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={cn(
          "w-full rounded-lg border-2 border-dashed px-6 py-10 text-center transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
          isDragging
            ? "border-primary bg-primary/5"
            : "border-muted-foreground/25 hover:border-muted-foreground/50 hover:bg-muted/30",
          disabled && "cursor-not-allowed opacity-50",
          error && "border-destructive",
        )}
        aria-label="Upload CSV file"
      >
        <Upload className="mx-auto mb-3 h-8 w-8 text-muted-foreground" />
        <p className="text-sm font-medium">
          Drag and drop a CSV file here, or{" "}
          <span className="text-primary underline-offset-4 hover:underline">
            click to browse
          </span>
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          .csv files only, max 5 MB
        </p>
      </button>
      {error && <p className="text-xs text-destructive">{error}</p>}
      <input
        ref={inputRef}
        type="file"
        accept=".csv"
        className="sr-only"
        onChange={handleInputChange}
        disabled={disabled}
      />
    </div>
  );
}
