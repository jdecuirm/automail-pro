import { Outlet } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import Sidebar from "@/components/layout/Sidebar";
import Topbar from "@/components/layout/Topbar";

export default function Layout() {
  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Sidebar — hidden on mobile, visible md+ */}
      <div className="hidden md:flex md:shrink-0">
        <Sidebar />
      </div>

      {/* Main area */}
      <div className="flex flex-1 flex-col min-w-0 overflow-hidden">
        <Topbar />
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>

      <Toaster position="bottom-right" richColors />
    </div>
  );
}
