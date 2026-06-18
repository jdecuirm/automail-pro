import { AlertCircle } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { CSVParseResult } from "@/lib/csv";

interface CSVPreviewTableProps {
  result: CSVParseResult;
}

export default function CSVPreviewTable({ result }: CSVPreviewTableProps) {
  const { headers, rows, totalRows, errors } = result;

  return (
    <div className="space-y-3">
      {errors.length > 0 && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            <ul className="list-disc list-inside space-y-0.5">
              {errors.map((err, i) => (
                <li key={i} className="text-xs">
                  {err}
                </li>
              ))}
            </ul>
          </AlertDescription>
        </Alert>
      )}

      <div className="flex items-center justify-between">
        <p className="text-xs text-muted-foreground">
          Showing first {rows.length} of{" "}
          <span className="font-medium text-foreground">{totalRows}</span> rows
          detected
        </p>
      </div>

      <ScrollArea className="h-52 rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              {headers.map((h) => (
                <TableHead key={h} className="text-xs whitespace-nowrap">
                  {h}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row, i) => (
              <TableRow key={i}>
                {headers.map((h) => (
                  <TableCell key={h} className="text-xs max-w-[160px] truncate">
                    {row[h] ?? ""}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </ScrollArea>
    </div>
  );
}
