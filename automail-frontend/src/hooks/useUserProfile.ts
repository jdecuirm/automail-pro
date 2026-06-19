import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getProfile, updateProfile } from "@/api/users";
import type { UserProfileUpdate } from "@/types/api";

export const USER_PROFILE_KEY = ["user", "profile"] as const;

export function useUserProfile() {
  return useQuery({
    queryKey: USER_PROFILE_KEY,
    queryFn: getProfile,
    staleTime: 1000 * 60 * 5, // 5 min — profile changes infrequently
  });
}

export function useUpdateProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: UserProfileUpdate) => updateProfile(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: USER_PROFILE_KEY });
    },
  });
}
