import { NavLink, Outlet } from "react-router-dom";
import { Mail, User } from "lucide-react";
import { cn } from "@/lib/utils";

const tabs = [
  { to: "/settings/account", label: "Account", icon: User },
  { to: "/settings/gmail", label: "Gmail", icon: Mail },
] as const;

export default function SettingsLayout() {
  return (
    <div className="flex gap-8">
      {/* Vertical sub-nav */}
      <nav className="w-44 shrink-0 space-y-1">
        {tabs.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end
            className={({ isActive }) =>
              cn(
                "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
              )
            }
          >
            <Icon className="h-4 w-4 shrink-0" />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Page content */}
      <div className="flex-1 min-w-0">
        <Outlet />
      </div>
    </div>
  );
}
