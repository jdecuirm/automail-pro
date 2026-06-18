import { useNavigate } from "react-router-dom";
import { LayoutDashboard, Send, Settings, Plus, Moon, Sun } from "lucide-react";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import { useCampaigns } from "@/hooks/useCampaigns";
import { useTheme } from "@/hooks/useTheme";

interface CommandPaletteProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export default function CommandPalette({
  open,
  onOpenChange,
}: CommandPaletteProps) {
  const navigate = useNavigate();
  const { data: campaigns } = useCampaigns();
  const { theme, setTheme } = useTheme();

  function run(fn: () => void) {
    onOpenChange(false);
    fn();
  }

  return (
    <CommandDialog open={open} onOpenChange={onOpenChange}>
      <CommandInput placeholder="Type a command or search…" />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>

        <CommandGroup heading="Navigation">
          <CommandItem onSelect={() => run(() => void navigate("/"))}>
            <LayoutDashboard className="mr-2 h-4 w-4" />
            Go to Dashboard
          </CommandItem>
          <CommandItem onSelect={() => run(() => void navigate("/campaigns"))}>
            <Send className="mr-2 h-4 w-4" />
            Go to Campaigns
          </CommandItem>
          <CommandItem
            onSelect={() => run(() => void navigate("/settings/gmail"))}
          >
            <Settings className="mr-2 h-4 w-4" />
            Go to Settings
          </CommandItem>
        </CommandGroup>

        <CommandSeparator />

        <CommandGroup heading="Quick actions">
          <CommandItem
            onSelect={() => run(() => void navigate("/campaigns/new"))}
          >
            <Plus className="mr-2 h-4 w-4" />
            Create new campaign
          </CommandItem>
          <CommandItem
            onSelect={() =>
              run(() => setTheme(theme === "dark" ? "light" : "dark"))
            }
          >
            {theme === "dark" ? (
              <Sun className="mr-2 h-4 w-4" />
            ) : (
              <Moon className="mr-2 h-4 w-4" />
            )}
            Toggle theme
          </CommandItem>
        </CommandGroup>

        {campaigns && campaigns.length > 0 && (
          <>
            <CommandSeparator />
            <CommandGroup heading="Recent campaigns">
              {campaigns.slice(0, 5).map((c) => (
                <CommandItem
                  key={c.id}
                  value={c.name}
                  onSelect={() =>
                    run(() => void navigate(`/campaigns/${c.id}`))
                  }
                >
                  <Send className="mr-2 h-4 w-4 text-muted-foreground" />
                  {c.name}
                </CommandItem>
              ))}
            </CommandGroup>
          </>
        )}
      </CommandList>
    </CommandDialog>
  );
}
