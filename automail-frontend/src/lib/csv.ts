import Papa from "papaparse";

export interface CSVParseResult {
  headers: string[];
  rows: Record<string, string>[];
  totalRows: number;
  errors: string[];
}

const REQUIRED_HEADERS = ["name", "email"];

export function parseCSVPreview(file: File): Promise<CSVParseResult> {
  return new Promise((resolve) => {
    Papa.parse<Record<string, string>>(file, {
      header: true,
      skipEmptyLines: true,
      complete(results) {
        const headers = results.meta.fields ?? [];
        const rows = results.data;
        const errors: string[] = [];

        const lowerHeaders = headers.map((h) => h.toLowerCase().trim());
        for (const required of REQUIRED_HEADERS) {
          if (!lowerHeaders.includes(required)) {
            errors.push(`Missing required column: "${required}"`);
          }
        }

        if (results.errors.length > 0) {
          errors.push(`CSV parse warning: ${results.errors[0].message}`);
        }

        resolve({
          headers,
          rows: rows.slice(0, 10),
          totalRows: rows.length,
          errors,
        });
      },
      error(err) {
        resolve({
          headers: [],
          rows: [],
          totalRows: 0,
          errors: [err.message],
        });
      },
    });
  });
}
