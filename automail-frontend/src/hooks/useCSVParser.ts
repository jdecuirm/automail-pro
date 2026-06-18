import { useState, useCallback } from "react";
import { parseCSVPreview } from "@/lib/csv";
import type { CSVParseResult } from "@/lib/csv";

const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5 MB

interface UseCSVParserReturn {
  result: CSVParseResult | null;
  isParsing: boolean;
  fileError: string | null;
  parse: (file: File) => Promise<void>;
  reset: () => void;
}

export function useCSVParser(): UseCSVParserReturn {
  const [result, setResult] = useState<CSVParseResult | null>(null);
  const [isParsing, setIsParsing] = useState(false);
  const [fileError, setFileError] = useState<string | null>(null);

  const parse = useCallback(async (file: File) => {
    setFileError(null);
    setResult(null);

    if (!file.name.toLowerCase().endsWith(".csv")) {
      setFileError("Only .csv files are accepted.");
      return;
    }
    if (file.size > MAX_FILE_SIZE) {
      setFileError("File is too large. Maximum size is 5 MB.");
      return;
    }

    setIsParsing(true);
    try {
      const parsed = await parseCSVPreview(file);
      setResult(parsed);
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
