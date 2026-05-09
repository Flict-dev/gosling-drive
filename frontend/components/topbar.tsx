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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
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
    <Card className="rounded-none border-x-0 border-t-0 shadow-sm">
      <CardHeader className="mx-auto flex w-full max-w-[1680px] flex-col gap-4 px-4 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-8">
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
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="rounded-full p-0"
                aria-label="Профиль пользователя"
              >
                <Avatar className="size-9">
                  <AvatarFallback>{getInitials(user.full_name)}</AvatarFallback>
                </Avatar>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-64">
              <DropdownMenuLabel className="font-normal">
                <div className="flex min-w-0 flex-col gap-1">
                  <span className="truncate text-sm font-medium text-foreground">
                    {user.full_name}
                  </span>
                  <span className="truncate text-xs text-muted-foreground">
                    {user.email}
                  </span>
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuGroup>
                <DropdownMenuItem onSelect={handleLogout}>
                  <LogOut data-icon="inline-start" />
                  Выйти
                </DropdownMenuItem>
              </DropdownMenuGroup>
            </DropdownMenuContent>
          </DropdownMenu>
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
