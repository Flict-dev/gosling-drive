"use client";

import { useCallback, useEffect, useState } from "react";

import {
  ApiError,
  api,
  type FileRead,
  type FolderRead,
  type StorageStats,
  type UserRead,
} from "@/lib/api";
import { clearToken, getToken } from "@/lib/auth";
import { AddResourceMenu } from "@/components/add-resource-menu";
import { AuthForm } from "@/components/auth-form";
import { FileList } from "@/components/file-list";
import { Skeleton } from "@/components/ui/skeleton";
import { Topbar } from "@/components/topbar";
import { toast } from "sonner";

type Mode = "loading" | "guest" | "authed";
type FolderPathItem = Pick<FolderRead, "id" | "name">;

export function Dashboard() {
  const [mode, setMode] = useState<Mode>("loading");
  const [user, setUser] = useState<UserRead | null>(null);
  const [folders, setFolders] = useState<FolderRead[]>([]);
  const [files, setFiles] = useState<FileRead[]>([]);
  const [stats, setStats] = useState<StorageStats | null>(null);
  const [filesLoading, setFilesLoading] = useState(false);
  const [currentPath, setCurrentPath] = useState<FolderPathItem[]>([]);

  const currentFolder = currentPath.at(-1) ?? null;
  const currentFolderId = currentFolder?.id ?? null;
  const currentFolderName = currentFolder?.name ?? "Мой диск";

  const loadDrive = useCallback(async (folderId: string | null) => {
    setFilesLoading(true);
    try {
      const folderQuery = folderId
        ? `?parent_id=${encodeURIComponent(folderId)}`
        : "";
      const fileQuery = folderId
        ? `?folder_id=${encodeURIComponent(folderId)}`
        : "";
      const [folderData, fileData, storageStats] = await Promise.all([
        api<FolderRead[]>(`/folders/${folderQuery}`),
        api<FileRead[]>(`/files/${fileQuery}`),
        api<StorageStats>("/storage/stats"),
      ]);
      setFolders(folderData);
      setFiles(fileData);
      setStats(storageStats);
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Ошибка загрузки папки"
      );
    } finally {
      setFilesLoading(false);
    }
  }, []);

  const refreshCurrentFolder = useCallback(async () => {
    await loadDrive(currentFolderId);
  }, [currentFolderId, loadDrive]);

  const bootstrap = useCallback(async () => {
    const token = getToken();
    if (!token) {
      setMode("guest");
      setUser(null);
      setFolders([]);
      setFiles([]);
      setStats(null);
      setCurrentPath([]);
      return;
    }
    try {
      const me = await api<UserRead>("/auth/me");
      setUser(me);
      setMode("authed");
      setCurrentPath([]);
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        clearToken();
      }
      setUser(null);
      setFolders([]);
      setFiles([]);
      setStats(null);
      setCurrentPath([]);
      setMode("guest");
    }
  }, []);

  const handleLoggedOut = useCallback(() => {
    setUser(null);
    setFolders([]);
    setFiles([]);
    setStats(null);
    setCurrentPath([]);
    setMode("guest");
  }, []);

  const handleOpenFolder = useCallback((folder: FolderRead) => {
    setCurrentPath((path) => [...path, { id: folder.id, name: folder.name }]);
  }, []);

  const handleNavigatePath = useCallback((index: number) => {
    setCurrentPath((path) => (index < 0 ? [] : path.slice(0, index + 1)));
  }, []);

  const handleGoUp = useCallback(() => {
    setCurrentPath((path) => path.slice(0, -1));
  }, []);

  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);

  useEffect(() => {
    if (mode === "authed") {
      void loadDrive(currentFolderId);
    }
  }, [currentFolderId, loadDrive, mode]);

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
      <div className="flex min-h-screen flex-col">
        <Topbar user={null} />
        <div className="mx-auto flex w-full max-w-[1680px] flex-1 justify-center px-4 py-8 sm:px-6 lg:px-8">
          <AuthForm onAuthenticated={bootstrap} />
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col">
      <Topbar user={user} stats={stats} onLogout={handleLoggedOut} />
      <div className="mx-auto flex w-full max-w-[1680px] flex-1 flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
        <FileList
          folders={folders}
          files={files}
          currentPath={currentPath}
          loading={filesLoading}
          addAction={
            <AddResourceMenu
              folderId={currentFolderId}
              folderName={currentFolderName}
              onChanged={refreshCurrentFolder}
              disabled={filesLoading}
            />
          }
          onGoUp={handleGoUp}
          onNavigatePath={handleNavigatePath}
          onOpenFolder={handleOpenFolder}
          onRefresh={refreshCurrentFolder}
        />
      </div>
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="flex min-h-screen flex-col">
      <Skeleton className="h-32 w-full rounded-none" />
      <div className="mx-auto flex w-full max-w-[1680px] flex-1 flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
        <Skeleton className="h-80 w-full" />
      </div>
    </div>
  );
}
