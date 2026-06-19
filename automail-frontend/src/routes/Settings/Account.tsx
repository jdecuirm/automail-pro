import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { User, CheckCircle2, AlertCircle } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { useUserProfile, useUpdateProfile } from "@/hooks/useUserProfile";

const schema = z.object({
  sender_name: z.string().min(1, "Name is required").max(120),
  sender_company: z.string().min(1, "Company is required").max(120),
});

type FormValues = z.infer<typeof schema>;

export default function SettingsAccount() {
  const { data: profile, isLoading } = useUserProfile();
  const {
    mutate: save,
    isPending,
    isSuccess,
    isError,
    error,
  } = useUpdateProfile();

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { sender_name: "", sender_company: "" },
  });

  useEffect(() => {
    if (profile) {
      form.reset({
        sender_name: profile.sender_name ?? "",
        sender_company: profile.sender_company ?? "",
      });
    }
  }, [profile, form]);

  function onSubmit(values: FormValues) {
    save(values);
  }

  const initials = profile?.sender_name
    ? profile.sender_name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2)
    : "?";

  return (
    <div className="max-w-lg space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Account</h1>
        <p className="text-sm text-muted-foreground">
          Configure how you appear in outreach emails
        </p>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-4">
            <Avatar className="h-14 w-14">
              <AvatarFallback className="text-lg">{initials}</AvatarFallback>
            </Avatar>
            <div>
              <CardTitle>{profile?.sender_name ?? "Your Name"}</CardTitle>
              <CardDescription className="flex items-center gap-1.5 mt-1">
                <User className="h-3 w-3" />
                {profile?.sender_company ?? "Your Company"}
              </CardDescription>
            </div>
          </div>
        </CardHeader>

        <CardContent>
          {!isLoading && !profile?.profile_complete && (
            <div className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/30 px-3 py-2 text-sm text-amber-800 dark:text-amber-300 mb-4">
              <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
              <span>
                Complete your sender profile so emails don't contain{" "}
                <code className="font-mono text-xs">[YOUR_NAME]</code> or{" "}
                <code className="font-mono text-xs">[YOUR_COMPANY]</code>{" "}
                placeholders. Sending is blocked until both fields are filled.
              </span>
            </div>
          )}

          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              <FormField
                control={form.control}
                name="sender_name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Your name</FormLabel>
                    <FormControl>
                      <Input placeholder="Jane Smith" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="sender_company"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Your company</FormLabel>
                    <FormControl>
                      <Input placeholder="Acme Corp" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="flex items-center gap-3 pt-1">
                <Button type="submit" disabled={isPending}>
                  {isPending ? "Saving…" : "Save profile"}
                </Button>

                {isSuccess && (
                  <span className="flex items-center gap-1.5 text-sm text-green-600 dark:text-green-400">
                    <CheckCircle2 className="h-4 w-4" />
                    Saved
                  </span>
                )}

                {isError && (
                  <span className="text-sm text-destructive">
                    {error instanceof Error ? error.message : "Failed to save"}
                  </span>
                )}
              </div>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  );
}
