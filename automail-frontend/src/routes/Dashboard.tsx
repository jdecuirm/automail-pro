import { Link } from "react-router-dom";
import { Mail, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useGmailStatus } from "@/hooks/useGmailStatus";

export default function Dashboard() {
  const { data: gmailStatus } = useGmailStatus();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        <p className="text-sm text-muted-foreground">
          AI-powered lead outreach automation
        </p>
      </div>

      <Card className="max-w-md">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
              {gmailStatus?.connected ? (
                <Send className="h-5 w-5 text-primary" />
              ) : (
                <Mail className="h-5 w-5 text-primary" />
              )}
            </div>
            <div>
              <CardTitle className="text-base">
                {gmailStatus?.connected ? "Ready to send" : "Get started"}
              </CardTitle>
              <CardDescription className="text-xs">
                {gmailStatus?.connected
                  ? "Your Gmail is connected"
                  : "Connect your Gmail first"}
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            {gmailStatus?.connected
              ? "Upload a CSV of leads to start a new outreach campaign."
              : "AutoMail Pro sends emails via your Gmail account. Connect it to get started."}
          </p>
        </CardContent>
        <CardFooter>
          {gmailStatus?.connected ? (
            <Button asChild className="w-full sm:w-auto">
              <Link to="/campaigns">Create your first campaign</Link>
            </Button>
          ) : (
            <Button asChild className="w-full sm:w-auto">
              <Link to="/settings/gmail">Connect your Gmail</Link>
            </Button>
          )}
        </CardFooter>
      </Card>
    </div>
  );
}
