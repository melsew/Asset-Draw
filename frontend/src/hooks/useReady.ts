import { useQuery } from "@tanstack/react-query";
import { fetchReady } from "../services/api";

export function useReady() {
  return useQuery({
    queryKey: ["health-ready"],
    queryFn: fetchReady,
    staleTime: 60_000,
    retry: 1,
  });
}
