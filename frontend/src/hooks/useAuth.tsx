"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  apiClient,
  clearAuthToken,
  getAuthToken,
  setAuthToken,
  type TokenResponse,
  type UserResponse,
} from "@/lib/api-client";

interface AuthContextType {
  user: UserResponse | null;
  token: string | null;
  isLoading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [token, setTokenState] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  // Rehydrate auth state on client mount
  useEffect(() => {
    async function loadUser() {
      const storedToken = getAuthToken();
      if (!storedToken) {
        setIsLoading(false);
        return;
      }

      setTokenState(storedToken);
      try {
        const userData = await apiClient<UserResponse>("/users/me");
        setUser(userData);
      } catch {
        clearAuthToken();
        setTokenState(null);
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    }

    loadUser();
  }, []);

  const login = async (email: string, password: string): Promise<void> => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await apiClient<TokenResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });

      setAuthToken(response.access_token);
      setTokenState(response.access_token);
      setUser(response.user);
      router.push("/");
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Authentication failed.";
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = (): void => {
    clearAuthToken();
    setTokenState(null);
    setUser(null);
    router.push("/login");
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        error,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
