import { useState, useEffect } from "react";
import { Outlet } from "react-router-dom";
import CommandPalette from "@/components/common/CommandPalette";
import ErrorBoundary from "@/components/common/ErrorBoundary";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { Toaster } from "@/components/ui/sonner";
import Sidebar from "@/components/layout/Sidebar";
import Topbar from "@/components/layout/Topbar";

export default function Layout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [cmdOpen, setCmdOpen] = useState(false);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setCmdOpen((prev) => !prev);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  function closeMobile() {
    setMobileOpen(false);
  }

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Desktop sidebar — visible md+ */}
      <div className="hidden md:flex md:shrink-0">
        <Sidebar />
      </div>

      {/* Mobile sidebar — Sheet slide-in */}
      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
        <SheetContent
          side="left"
          className="p-0"
          style={{ width: "240px" }}
          showCloseButton={false}
        >
          <SheetTitle className="sr-only">Navigation</SheetTitle>
          <Sidebar onNavClick={closeMobile} onClose={closeMobile} />
        </SheetContent>
      </Sheet>

      {/* Main area */}
      <div className="flex flex-1 flex-col min-w-0 overflow-hidden">
        <Topbar
          onMenuClick={() => {
            setMobileOpen(true);
          }}
        />
        <main className="flex-1 overflow-y-auto p-4 md:p-6">
          <ErrorBoundary>
            <Outlet />
          </ErrorBoundary>
        </main>
      </div>

      <Toaster position="bottom-right" richColors />
      {cmdOpen && <CommandPalette open={cmdOpen} onOpenChange={setCmdOpen} />}
    </div>
  );
}
