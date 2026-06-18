import { useState, useCallback } from "react";
import { toast } from "sonner";
import { parseCSVPreview } from "@/lib/csv";
import type { CSVParseResult } from "@/lib/csv";

const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5 MB

const ACCEPTED_MIMES = new Set([
  "text/csv",
  "application/vnd.ms-excel",
  "text/plain",
  "application/csv",
  "", // some browsers report empty string for .csv files
]);

interface UseCSVParserReturn {
  result: CSVParseResult | null;
  isParsing: boolean;
  fileError: string | null;
  parse: (file: File) => Promise<boolean>;
  reset: () => void;
}

export function useCSVParser(): UseCSVParserReturn {
  const [result, setResult] = useState<CSVParseResult | null>(null);
  const [isParsing, setIsParsing] = useState(false);
  const [fileError, setFileError] = useState<string | null>(null);

  const parse = useCallback(async (file: File): Promise<boolean> => {
    setFileError(null);
    setResult(null);

    if (!file.name.toLowerCase().endsWith(".csv")) {
      const msg = `Only CSV files are accepted. Got: ${file.name.split(".").pop() ?? "unknown"}`;
      setFileError(msg);
      toast.error(msg);
      return false;
    }

    const mime = file.type.toLowerCase().split(";")[0].trim();
    if (!ACCEPTED_MIMES.has(mime)) {
      const msg = `Only CSV files are accepted. Got: ${mime || "unknown type"}`;
      setFileError(msg);
      toast.error(msg);
      return false;
    }

    if (file.size > MAX_FILE_SIZE) {
      setFileError("File is too large. Maximum size is 5 MB.");
      return false;
    }

    setIsParsing(true);
    try {
      const parsed = await parseCSVPreview(file);
      setResult(parsed);
      return true;
    } finally {
      setIsParsing(false);
    }
  }, []);

  const reset = useCallback(() => {
    setResult(null);
    setFileError(null);
    setIsParsing(false);
  }, []);

  return { result, isParsing, fileError, parse, reset };
}
