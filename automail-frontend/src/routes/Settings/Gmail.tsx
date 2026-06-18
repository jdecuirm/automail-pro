import { useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { CheckCircle2, LogOut, Mail, Shield, User } from "lucide-react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { disconnectGmail } from "@/api/oauth";
import { useGmailStatus } from "@/hooks/useGmailStatus";
import { apiBaseUrl } from "@/api/client";

export default function SettingsGmail() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { data: gmailStatus, isPending } = useGmailStatus();
  const queryClient = useQueryClient();

  // Handle OAuth callback redirect (?oauth_success=true)
  useEffect(() => {
    if (searchParams.get("oauth_success") === "true") {
      toast.success("Gmail connected successfully!");
      setSearchParams({}, { replace: true });
      void queryClient.invalidateQueries({ queryKey: ["gmail-status"] });
    }
  }, [searchParams, setSearchParams, queryClient]);

  const disconnectMutation = useMutation({
    mutationFn: disconnectGmail,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["gmail-status"] });
      toast.success("Gmail disconnected.");
    },
    onError: () => {
      toast.error("Failed to disconnect Gmail. Try again.");
    },
  });

  function handleConnect() {
    window.location.href = `${apiBaseUrl}/api/oauth/google/authorize`;
  }

  if (isPending) {
    return (
      <div className="max-w-lg space-y-4">
        <Skeleton className="h-8 w-40" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  return (
    <div className="max-w-lg space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Gmail Integration</h1>
        <p className="text-sm text-muted-foreground">
          Connect your Gmail to send outreach emails on your behalf.
        </p>
      </div>

      {gmailStatus?.connected ? (
        <Card>
          <CardHeader>
            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
              <Avatar className="h-12 w-12">
                <AvatarFallback className="bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">
                  {gmailStatus.email_address
                    ? gmailStatus.email_address[0].toUpperCase()
                    : "G"}
                </AvatarFallback>
              </Avatar>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <CardTitle className="text-base truncate">
                    {gmailStatus.email_address ?? "Gmail account"}
                  </CardTitle>
                  <Badge
                    variant="outline"
                    className="shrink-0 border-green-500 text-green-600 dark:text-green-400"
                  >
                    <CheckCircle2 className="mr-1 h-3 w-3" />
                    Connected
                  </Badge>
                </div>
                <CardDescription className="text-xs mt-0.5">
                  AutoMail Pro can send emails via this account
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {gmailStatus.needs_reconnect && (
              <div className="rounded-md bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 px-3 py-2 text-xs text-yellow-800 dark:text-yellow-300">
                Your Gmail credentials have expired. Please reconnect.
              </div>
            )}
            <div className="text-sm text-muted-foreground">
              Daily send quota:{" "}
              <span className="font-medium text-foreground">
                50 emails / day
              </span>
            </div>
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button
                  variant="destructive"
                  size="sm"
                  className="gap-2 w-full sm:w-auto"
                  disabled={disconnectMutation.isPending}
                >
                  <LogOut className="h-4 w-4" />
                  {disconnectMutation.isPending
                    ? "Disconnecting…"
                    : "Disconnect Gmail"}
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Disconnect Gmail?</AlertDialogTitle>
                  <AlertDialogDescription>
                    AutoMail Pro will no longer be able to send emails on your
                    behalf. Any unsent approved emails will need to be
                    re-approved after reconnecting.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction
                    className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                    onClick={() => {
                      disconnectMutation.mutate();
                    }}
                  >
                    Yes, disconnect
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted mb-2">
              <Mail className="h-6 w-6 text-muted-foreground" />
            </div>
            <CardTitle>Connect your Gmail</CardTitle>
            <CardDescription>
              AutoMail Pro needs access to your Gmail account to send outreach
              emails on your behalf using Google&apos;s official API.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li className="flex items-center gap-2">
                <Shield className="h-4 w-4 shrink-0 text-green-500" />
                Send emails on your behalf (up to 50/day)
              </li>
              <li className="flex items-center gap-2">
                <User className="h-4 w-4 shrink-0 text-green-500" />
                View your primary email address
              </li>
            </ul>
            <Button onClick={handleConnect} className="w-full gap-2">
              <Mail className="h-4 w-4" />
              Connect with Google
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
