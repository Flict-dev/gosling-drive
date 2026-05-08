"use client";

import { useCallback, useEffect, useState } from "react";

import {
  ApiError,
  api,
  type FileRead,
  type StorageStats,
  type UserRead,
} from "@/lib/api";
import { clearToken, getToken } from "@/lib/auth";
import { AuthForm } from "@/components/auth-form";
import { FileList } from "@/components/file-list";
import { FolderCard } from "@/components/folder-card";
import { Skeleton } from "@/components/ui/skeleton";
import { Topbar } from "@/components/topbar";
import { UploadCard } from "@/components/upload-card";

type Mode = "loading" | "guest" | "authed";

export function Dashboard() {
  const [mode, setMode] = useState<Mode>("loading");
  const [user, setUser] = useState<UserRead | null>(null);
  const [files, setFiles] = useState<FileRead[]>([]);
  const [stats, setStats] = useState<StorageStats | null>(null);
  const [filesLoading, setFilesLoading] = useState(false);

  const loadFiles = useCallback(async () => {
    setFilesLoading(true);
    try {
      const [fileData, storageStats] = await Promise.all([
        api<FileRead[]>("/files/"),
        api<StorageStats>("/storage/stats"),
      ]);
      setFiles(fileData);
      setStats(storageStats);
    } finally {
      setFilesLoading(false);
    }
  }, []);

  const bootstrap = useCallback(async () => {
    const token = getToken();
    if (!token) {
      setMode("guest");
      setUser(null);
      setFiles([]);
      setStats(null);
      return;
    }
    try {
      const me = await api<UserRead>("/auth/me");
      setUser(me);
      setMode("authed");
      await loadFiles();
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        clearToken();
      }
      setUser(null);
      setStats(null);
      setMode("guest");
    }
  }, [loadFiles]);

  const handleLoggedOut = useCallback(() => {
    setUser(null);
    setFiles([]);
    setStats(null);
    setMode("guest");
  }, []);

  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);

  useEffect(() => {
    function onStorage(event: StorageEvent) {
      if (event.key === "gosling_drive_token") {
        void bootstrap();
      }
    }
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, [bootstrap]);

  if (mode === "loading") {
    return <DashboardSkeleton />;
  }

  if (mode === "guest") {
    return (
      <div className="flex flex-col gap-6">
        <Topbar user={null} />
        <div className="flex justify-center pt-8">
          <AuthForm onAuthenticated={bootstrap} />
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <Topbar user={user} stats={stats} onLogout={handleLoggedOut} />
      <div className="grid gap-6 md:grid-cols-2">
        <UploadCard onUploaded={loadFiles} />
        <FolderCard onCreated={loadFiles} />
      </div>
      <FileList
        files={files}
        loading={filesLoading}
        onRefresh={loadFiles}
      />
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="flex flex-col gap-6">
      <Skeleton className="h-36 w-full" />
      <div className="grid gap-6 md:grid-cols-2">
        <Skeleton className="h-64 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
      <Skeleton className="h-80 w-full" />
    </div>
  );
}
