import { useQuery } from "@tanstack/react-query";
import { fetchCampaigns, fetchCampaign, fetchMyEntries } from "../services/api";

export function useCampaigns(params?: { status?: string; category?: string; search?: string }) {
  return useQuery({
    queryKey: ["campaigns", params],
    queryFn: () => fetchCampaigns(params),
    staleTime: 30_000,
  });
}

export function useCampaign(id: string) {
  return useQuery({
    queryKey: ["campaign", id],
    queryFn: () => fetchCampaign(id),
    staleTime: 30_000,
    enabled: !!id,
  });
}

export function useMyEntries() {
  return useQuery({
    queryKey: ["my-entries"],
    queryFn: fetchMyEntries,
    staleTime: 15_000,
  });
}
