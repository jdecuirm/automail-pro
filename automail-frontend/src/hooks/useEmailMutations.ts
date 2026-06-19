import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  approveEmail,
  rejectEmail,
  updateEmail,
  bulkSendApproved,
} from "@/api/emails";
import type { EmailUpdateRequest } from "@/types/api";

function invalidateEmailQueries(
  queryClient: ReturnType<typeof useQueryClient>,
  campaignId: string,
) {
  void queryClient.invalidateQueries({
    queryKey: ["campaign-emails", campaignId],
  });
  void queryClient.invalidateQueries({ queryKey: ["campaign", campaignId] });
}

export function useApproveEmail(campaignId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (emailId: string) => approveEmail(emailId),
    onSuccess() {
      invalidateEmailQueries(queryClient, campaignId);
      toast.success("Email approved and queued for sending.");
    },
    onError() {
      toast.error("Failed to approve email.");
    },
  });
}

export function useRejectEmail(campaignId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (emailId: string) => rejectEmail(emailId),
    onSuccess() {
      invalidateEmailQueries(queryClient, campaignId);
      toast.success("Email rejected.");
    },
    onError() {
      toast.error("Failed to reject email.");
    },
  });
}

export function useUpdateEmail(campaignId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: EmailUpdateRequest }) =>
      updateEmail(id, data),
    onSuccess() {
      invalidateEmailQueries(queryClient, campaignId);
      toast.success("Email updated.");
    },
    onError() {
      toast.error("Failed to save changes.");
    },
  });
}

export function useBulkSend(campaignId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => bulkSendApproved(campaignId),
    onSuccess(data) {
      invalidateEmailQueries(queryClient, campaignId);
      void queryClient.invalidateQueries({ queryKey: ["gmail-status"] });
      if (data.blocked_by_quota > 0) {
        toast.info(
          `${data.dispatched} emails queued. ${data.blocked_by_quota} held — daily quota reached.`,
        );
      } else {
        toast.success(
          `${data.dispatched} email${data.dispatched === 1 ? "" : "s"} queued for sending.`,
        );
      }
    },
    onError() {
      toast.error("Failed to send emails.");
    },
  });
}
