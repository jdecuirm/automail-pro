import { Link, NavLink } from "react-router-dom";
import { LayoutDashboard, Mail, Settings, Send } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { cn } from "@/lib/utils";
import ThemeToggle from "./ThemeToggle";

const navItems = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/campaigns", label: "Campaigns", icon: Send, end: false },
  { to: "/settings/gmail", label: "Settings", icon: Settings, end: false },
] as const;

function NavItem({
  to,
  label,
  icon: Icon,
  end,
}: {
  to: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  end: boolean;
}) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        cn(
          "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
          isActive
            ? "bg-accent text-accent-foreground"
            : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
        )
      }
    >
      <Icon className="h-4 w-4 shrink-0" />
      {label}
    </NavLink>
  );
}

export default function Sidebar() {
  return (
    <aside className="flex h-full w-60 flex-col border-r bg-sidebar">
      {/* Logo */}
      <div className="flex h-14 items-center gap-2 border-b px-4">
        <Mail className="h-5 w-5 text-primary" />
        <Link to="/" className="text-sm font-semibold tracking-tight">
          AutoMail Pro
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-2 py-4 space-y-1">
        {navItems.map((item) => (
          <NavItem key={item.to} {...item} />
        ))}
      </nav>

      {/* Footer */}
      <div className="flex items-center justify-between border-t px-3 py-3">
        <div className="flex items-center gap-2 min-w-0">
          <Avatar className="h-7 w-7 shrink-0">
            <AvatarFallback className="text-xs">JD</AvatarFallback>
          </Avatar>
          <span className="truncate text-xs text-muted-foreground">
            Demo User
          </span>
        </div>
        <ThemeToggle />
      </div>
    </aside>
  );
}
