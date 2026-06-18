import { useLocation, useNavigate } from "react-router-dom";
import { Menu, Wifi, WifiOff } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useGmailStatus } from "@/hooks/useGmailStatus";

const BREADCRUMBS: Record<string, string> = {
  "/": "Dashboard",
  "/campaigns": "Campaigns",
  "/settings/gmail": "Settings / Gmail",
  "/settings/account": "Settings / Account",
};

export default function Topbar({ onMenuClick }: { onMenuClick: () => void }) {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const { data: gmailStatus, isPending } = useGmailStatus();

  const breadcrumb =
    BREADCRUMBS[pathname] ?? pathname.replace(/\//g, " / ").trim();

  function handleGmailBadgeClick() {
    void navigate("/settings/gmail");
  }

  return (
    <header className="flex h-14 items-center justify-between border-b bg-background px-4 md:px-6">
      {/* Left side */}
      <div className="flex items-center gap-2">
        {/* Hamburger — only on mobile */}
        <Button
          variant="ghost"
          size="icon"
          className="md:hidden"
          onClick={onMenuClick}
          aria-label="Open navigation"
        >
          <Menu className="h-5 w-5" />
        </Button>
        {/* Breadcrumb — hide on very small screens */}
        <span className="hidden sm:block text-sm font-medium text-foreground">
          {breadcrumb}
        </span>
      </div>

      {/* Right side — Gmail status badge */}
      <button
        onClick={handleGmailBadgeClick}
        className="flex items-center gap-1.5 rounded-md px-2 py-1 text-xs transition-colors hover:bg-accent"
        aria-label="Gmail connection status"
      >
        {isPending ? (
          <Skeleton className="h-5 w-24" />
        ) : gmailStatus?.connected ? (
          <>
            <Wifi className="h-3.5 w-3.5 text-green-500" />
            <Badge
              variant="outline"
              className="border-green-500 text-green-600 dark:text-green-400"
            >
              Gmail connected
            </Badge>
          </>
        ) : (
          <>
            <WifiOff className="h-3.5 w-3.5 text-destructive" />
            <Badge variant="destructive">Gmail disconnected</Badge>
          </>
        )}
      </button>
    </header>
  );
}
