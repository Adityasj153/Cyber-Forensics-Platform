"use client";

import { useSession } from "next-auth/react";
import { ReactNode } from "react";

export type Role = "admin" | "investigator" | "viewer";

export function useRole(): Role | null {
  const { data: session } = useSession();
  return (session as any)?.user?.role ?? null;
}

export function RoleGate({
  roles,
  children,
  fallback = null,
}: {
  roles: Role[];
  children: ReactNode;
  fallback?: ReactNode;
}) {
  const role = useRole();
  if (!role || !roles.includes(role)) return <>{fallback}</>;
  return <>{children}</>;
}
