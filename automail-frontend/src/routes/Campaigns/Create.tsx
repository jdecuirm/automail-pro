import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
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
import { Separator } from "@/components/ui/separator";
import CSVUploader from "@/components/campaigns/CSVUploader";
import CSVPreviewTable from "@/components/campaigns/CSVPreviewTable";
import { useCSVParser } from "@/hooks/useCSVParser";
import { createCampaign } from "@/api/campaigns";

const schema = z.object({
  name: z.string().min(1, "Name is required").max(100, "Max 100 characters"),
});

type FormValues = z.infer<typeof schema>;

export default function CreateCampaign() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const {
    result: csvResult,
    isParsing,
    fileError,
    parse,
    reset,
  } = useCSVParser();

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { name: "" },
  });

  const mutation = useMutation({
    mutationFn: (values: FormValues) => {
      const formData = new FormData();
      formData.append("name", values.name);
      formData.append("file", csvFile!);
      return createCampaign(formData);
    },
    onSuccess(data) {
      void queryClient.invalidateQueries({ queryKey: ["campaigns"] });
      if (data.invalid_leads > 0) {
        toast.warning(
          `Campaign created with ${data.invalid_leads} invalid row(s) skipped.`,
        );
      } else {
        toast.success("Campaign created! Processing has started.");
      }
      void navigate(`/campaigns/${data.campaign_id}`);
    },
    onError() {
      toast.error("Failed to create campaign. Please try again.");
    },
  });

  async function handleFile(file: File) {
    const valid = await parse(file);
    setCsvFile(valid ? file : null);
  }

  function handleClear() {
    setCsvFile(null);
    reset();
  }

  function onSubmit(values: FormValues) {
    if (!csvFile) {
      toast.error("Please upload a CSV file.");
      return;
    }
    mutation.mutate(values);
  }

  const hasHeaderErrors =
    csvResult !== null &&
    csvResult.errors.some((e) => e.includes("Missing required"));
  const canSubmit =
    form.formState.isValid &&
    csvFile !== null &&
    fileError === null &&
    !hasHeaderErrors &&
    !mutation.isPending;

  return (
    <div className="max-w-2xl space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => void navigate("/campaigns")}
          aria-label="Back to campaigns"
        >
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-2xl font-semibold">Create Campaign</h1>
          <p className="text-sm text-muted-foreground">
            Upload a CSV of leads to start a new outreach campaign.
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Campaign details</CardTitle>
          <CardDescription>
            Give your campaign a name and upload your lead list.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
              {/* Name */}
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Name *</FormLabel>
                    <FormControl>
                      <Input
                        placeholder="e.g. SaaS Founders Q3 Outreach"
                        {...field}
                        disabled={mutation.isPending}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <Separator />

              {/* CSV Upload */}
              <div className="space-y-3">
                <div>
                  <p className="text-sm font-medium leading-none mb-1">
                    Lead list (CSV) *
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Required columns: <code className="font-mono">name</code>,{" "}
                    <code className="font-mono">email</code>. Optional:{" "}
                    <code className="font-mono">company</code>,{" "}
                    <code className="font-mono">website</code>,{" "}
                    <code className="font-mono">linkedin_url</code>
                  </p>
                </div>
                <CSVUploader
                  file={csvFile}
                  error={fileError}
                  onFile={handleFile}
                  onClear={handleClear}
                  disabled={mutation.isPending}
                />
              </div>

              {/* CSV Preview */}
              {isParsing && (
                <p className="text-xs text-muted-foreground">Parsing CSV…</p>
              )}
              {csvResult && !isParsing && (
                <CSVPreviewTable result={csvResult} />
              )}

              {/* Submit */}
              <div className="flex justify-end pt-2">
                <Button
                  type="submit"
                  disabled={!canSubmit}
                  className="min-w-[200px]"
                >
                  {mutation.isPending
                    ? "Creating…"
                    : "Create Campaign & Start Processing"}
                </Button>
              </div>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  );
}
