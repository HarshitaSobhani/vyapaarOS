"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, useSyncExternalStore } from "react";
import { Boxes, FileText, LayoutDashboard, LogOut, Settings, Sparkles, Users, Wallet } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api/endpoints";
import { clearToken, getToken } from "@/lib/auth";
import { cn } from "@/lib/utils";
import type { User } from "@/types/api";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/collections", label: "Collections", icon: Wallet },
  { href: "/inventory", label: "Inventory", icon: Boxes },
  { href: "/invoices", label: "Invoices", icon: FileText },
  { href: "/customers", label: "Customers", icon: Users },
  { href: "/assistant", label: "AI Assistant", icon: Sparkles },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  // Server snapshot is false so nothing renders (or fetches) before the browser confirms a token exists.
  const signedIn = useSyncExternalStore(() => () => {}, () => getToken() !== null, () => false);

  useEffect(() => {
    if (!signedIn) {
      if (typeof window !== "undefined" && getToken() === null) router.replace("/login");
      return;
    }
    api.me().then(setUser).catch(() => undefined); // a 401 is handled centrally by the API client
  }, [signedIn, router]);

  function logout() {
    clearToken();
    router.replace("/login");
  }

  return (
    <div className="min-h-screen bg-muted/30 lg:flex">
      <aside className="border-b bg-background lg:sticky lg:top-0 lg:h-screen lg:w-56 lg:shrink-0 lg:border-r lg:border-b-0">
        <div className="flex items-center justify-between px-4 py-3 lg:py-5">
          <Link href="/dashboard" className="text-lg font-semibold tracking-tight">
            Vyapaar<span className="text-emerald-600">OS</span>
          </Link>
          <Button variant="ghost" size="icon-sm" className="lg:hidden" onClick={logout} aria-label="Sign out">
            <LogOut />
          </Button>
        </div>
        <nav aria-label="Main" className="flex gap-1 overflow-x-auto px-2 pb-2 lg:flex-col lg:pb-0">
          {NAV.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || pathname.startsWith(`${href}/`);
            return (
              <Link
                key={href}
                href={href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex shrink-0 items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors",
                  active ? "bg-muted font-medium text-foreground" : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
                )}
              >
                <Icon className="size-4" />
                {label}
              </Link>
            );
          })}
        </nav>
        <div className="mt-auto hidden border-t p-3 lg:absolute lg:bottom-0 lg:block lg:w-56">
          <p className="truncate text-sm font-medium">{user?.name ?? " "}</p>
          <p className="truncate text-xs text-muted-foreground">{user ? `${user.role} · ${user.email}` : " "}</p>
          <Button variant="ghost" size="sm" className="mt-2 w-full justify-start" onClick={logout}>
            <LogOut /> Sign out
          </Button>
        </div>
      </aside>
      <main className="min-w-0 flex-1 p-4 lg:p-8">{signedIn ? children : null}</main>
    </div>
  );
}
