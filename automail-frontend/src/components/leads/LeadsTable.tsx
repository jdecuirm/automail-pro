import { useState, useMemo } from "react";
import {
  useReactTable,
  getCoreRowModel,
  flexRender,
  createColumnHelper,
} from "@tanstack/react-table";
import { Search, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import LeadStatusBadge from "./LeadStatusBadge";
import LeadDetailDialog from "./LeadDetailDialog";
import DataTablePagination from "@/components/common/DataTablePagination";
import { useCampaignLeads } from "@/hooks/useCampaignLeads";
import { relativeTime } from "@/lib/format";
import type { LeadResponse, LeadStatus, CampaignStatus } from "@/types/api";

const columnHelper = createColumnHelper<LeadResponse>();

const ALL_LEAD_STATUSES: LeadStatus[] = [
  "uploaded",
  "scraping",
  "researched",
  "generating",
  "drafted",
  "approved",
  "rejected",
  "sending",
  "sent",
  "opened",
  "failed",
];

interface LeadsTableProps {
  campaignId: string;
  campaignStatus?: CampaignStatus;
}

export default function LeadsTable({
  campaignId,
  campaignStatus,
}: LeadsTableProps) {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [statusFilter, setStatusFilter] = useState<LeadStatus | "">("");
  const [selectedLead, setSelectedLead] = useState<LeadResponse | null>(null);

  const { data, isPending, refetch, isRefetching } = useCampaignLeads(
    campaignId,
    {
      page,
      page_size: 20,
      status: statusFilter || undefined,
      search: search || undefined,
    },
    campaignStatus,
  );

  function handleSearch() {
    setSearch(searchInput);
    setPage(1);
  }

  function handleStatusChange(value: LeadStatus | "") {
    setStatusFilter(value);
    setPage(1);
  }

  function handleReset() {
    setSearch("");
    setSearchInput("");
    setStatusFilter("");
    setPage(1);
  }

  const hasFilters = search !== "" || statusFilter !== "";

  const columns = useMemo(
    () => [
      columnHelper.accessor("name", {
        header: "Name",
        cell: ({ getValue }) => (
          <span className="font-medium text-sm">{getValue()}</span>
        ),
      }),
      columnHelper.accessor("email", {
        header: "Email",
        cell: ({ getValue }) => (
          <span className="text-sm text-muted-foreground truncate max-w-[180px] block">
            {getValue()}
          </span>
        ),
      }),
      columnHelper.accessor("company", {
        header: "Company",
        cell: ({ getValue }) => (
          <span className="text-sm">
            {getValue() ?? <span className="text-muted-foreground">—</span>}
          </span>
        ),
      }),
      columnHelper.accessor("status", {
        header: "Status",
        cell: ({ getValue }) => <LeadStatusBadge status={getValue()} />,
      }),
      columnHelper.accessor("updated_at", {
        header: "Updated",
        cell: ({ getValue }) => (
          <span className="text-xs text-muted-foreground">
            {relativeTime(getValue())}
          </span>
        ),
      }),
      columnHelper.display({
        id: "actions",
        cell: ({ row }) => (
          <Button
            variant="ghost"
            size="sm"
            className="h-7 text-xs"
            onClick={() => setSelectedLead(row.original)}
          >
            View
          </Button>
        ),
      }),
    ],
    [setSelectedLead],
  );

  const table = useReactTable({
    data: data?.items ?? [],
    columns,
    getCoreRowModel: getCoreRowModel(),
    manualPagination: true,
  });

  return (
    <div className="space-y-3">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex items-center gap-1">
          <Input
            placeholder="Search by name or email…"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleSearch();
            }}
            className="h-8 text-sm max-w-[220px]"
          />
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            onClick={handleSearch}
            aria-label="Search"
          >
            <Search className="h-3.5 w-3.5" />
          </Button>
        </div>
        <Select
          value={statusFilter === "" ? "all" : statusFilter}
          onValueChange={(v) =>
            handleStatusChange(v === "all" ? "" : (v as LeadStatus))
          }
        >
          <SelectTrigger className="h-8 w-[180px] text-sm">
            <SelectValue placeholder="All statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            {ALL_LEAD_STATUSES.map((s) => (
              <SelectItem key={s} value={s}>
                {s.charAt(0).toUpperCase() + s.slice(1)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {hasFilters && (
          <Button
            variant="ghost"
            size="sm"
            className="h-8 text-xs"
            onClick={handleReset}
          >
            Reset
          </Button>
        )}
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 ml-auto"
          onClick={() => void refetch()}
          disabled={isRefetching}
          aria-label="Refresh leads"
        >
          <RefreshCw
            className={`h-3.5 w-3.5 ${isRefetching ? "animate-spin" : ""}`}
          />
        </Button>
      </div>

      {/* Table */}
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((hg) => (
              <TableRow key={hg.id}>
                {hg.headers.map((h) => (
                  <TableHead key={h.id}>
                    {flexRender(h.column.columnDef.header, h.getContext())}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {isPending ? (
              Array.from({ length: 5 }).map((_, i) => (
                <TableRow key={i}>
                  {columns.map((_, ci) => (
                    <TableCell key={ci}>
                      <Skeleton className="h-4 w-full" />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : table.getRowModel().rows.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={columns.length}
                  className="h-24 text-center text-sm text-muted-foreground"
                >
                  No leads found.
                </TableCell>
              </TableRow>
            ) : (
              table.getRowModel().rows.map((row) => (
                <TableRow key={row.id}>
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext(),
                      )}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      {data && (
        <DataTablePagination
          page={page}
          pageSize={20}
          total={data.total}
          onPageChange={setPage}
        />
      )}

      {/* Detail dialog */}
      <LeadDetailDialog
        lead={selectedLead}
        onClose={() => setSelectedLead(null)}
      />
    </div>
  );
}
