import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export function useUnreadCount(): number {
  const { can } = useAuth();
  const { data } = useQuery({
    queryKey: ["notifications", "unread-count"],
    queryFn: () => api.get<{ unread: number }>("/notifications/unread-count"),
    enabled: can("notifications:view"),
    refetchInterval: 60_000,
    retry: false,
  });
  return data?.unread ?? 0;
}
