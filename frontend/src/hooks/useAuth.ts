import { useState, useEffect, useCallback } from "react";
import { fetchMe, clearToken, getToken, logout, refreshAccessToken } from "../services/api";
import type { AuthUser } from "../types/auth";

export function useAuth() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      if (!getToken()) await refreshAccessToken();
      const me = await fetchMe();
      setUser(me);
    } catch {
      clearToken();
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);

  const signOut = useCallback(() => {
    clearToken();
    setUser(null);
    void logout();
  }, []);

  return { user, loading, refresh, signOut, isLoggedIn: !!user };
}
