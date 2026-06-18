import { User } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function SettingsAccount() {
  return (
    <div className="max-w-lg space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Account</h1>
        <p className="text-sm text-muted-foreground">
          Your profile information
        </p>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-4">
            <Avatar className="h-14 w-14">
              <AvatarFallback className="text-lg">JD</AvatarFallback>
            </Avatar>
            <div>
              <CardTitle>Demo User</CardTitle>
              <CardDescription className="flex items-center gap-2 mt-1">
                <User className="h-3 w-3" />
                Portfolio demo account
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <Badge variant="secondary" className="text-xs">
            Multi-user authentication coming in a future update
          </Badge>
        </CardContent>
      </Card>
    </div>
  );
}
