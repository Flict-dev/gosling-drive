"use client";

import { LogOut } from "lucide-react";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import type { StorageStats, UserRead } from "@/lib/api";
import { clearToken } from "@/lib/auth";
import { formatBytes } from "@/lib/utils";

type TopbarProps = {
  user: UserRead | null;
  stats?: StorageStats | null;
  onLogout?: () => void;
};

export function Topbar({ user, stats, onLogout }: TopbarProps) {
  function handleLogout() {
    clearToken();
    onLogout?.();
  }

  return (
    <Card>
      <CardHeader className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-col gap-1">
          <CardDescription>Gosling Drive</CardDescription>
          <CardTitle className="text-2xl">Файловое хранилище</CardTitle>
          {stats ? (
            <div className="flex flex-wrap gap-2 pt-2">
              <Badge variant="secondary">Файлов: {stats.files_count}</Badge>
              <Badge variant="outline">
                Объём: {formatBytes(stats.total_size_bytes)}
              </Badge>
            </div>
          ) : null}
        </div>
        {user ? (
          <div className="flex items-center gap-3">
            <Avatar className="size-9">
              <AvatarFallback>{getInitials(user.full_name)}</AvatarFallback>
            </Avatar>
            <div className="hidden min-w-0 text-right text-sm text-muted-foreground sm:block">
              <div className="truncate font-medium text-foreground">
                {user.full_name}
              </div>
              <div className="truncate">{user.email}</div>
            </div>
            <Separator orientation="vertical" className="hidden h-10 sm:block" />
            <Button variant="outline" size="sm" onClick={handleLogout}>
              <LogOut data-icon="inline-start" />
              Выйти
            </Button>
          </div>
        ) : null}
      </CardHeader>
    </Card>
  );
}

function getInitials(name: string): string {
  const initials = name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();

  return initials || "GD";
}
