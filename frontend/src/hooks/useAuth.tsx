"use client";

import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
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
  isAuthenticated: boolean;
  isAdmin: boolean;
  hasRole: (roles: string[]) => boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (organizationName: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
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

  const register = async (
    organizationName: string,
    email: string,
    password: string
  ): Promise<void> => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await apiClient<TokenResponse>("/auth/register", {
        method: "POST",
        body: JSON.stringify({
          organization_name: organizationName,
          email,
          password,
        }),
      });

      setAuthToken(response.access_token);
      setTokenState(response.access_token);
      setUser(response.user);
      router.push("/");
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Registration failed.";
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async (): Promise<void> => {
    try {
      await apiClient("/auth/logout", { method: "POST" });
    } catch {
      // Gracefully handle network/session invalidation edge cases
    } finally {
      clearAuthToken();
      setTokenState(null);
      setUser(null);
      router.push("/login");
    }
  };

  const hasRole = useCallback(
    (roles: string[]): boolean => {
      if (!user) return false;
      return roles.includes(user.role);
    },
    [user]
  );

  const isAuthenticated = Boolean(user && token);
  const isAdmin = user?.role === "Admin";

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        error,
        isAuthenticated,
        isAdmin,
        hasRole,
        login,
        register,
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

