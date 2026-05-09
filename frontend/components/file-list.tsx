"use client";

import { Fragment, type ChangeEvent, useRef, useState } from "react";
import {
  ArrowUp,
  ChevronRight,
  Download,
  FileIcon,
  Folder,
  FolderOpen,
  Home,
  History,
  Link as LinkIcon,
  RefreshCw,
} from "lucide-react";
import { toast } from "sonner";

import {
  api,
  type FileRead,
  type FolderRead,
  type ShareLinkRead,
} from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/ui/spinner";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { uploadLargeFile } from "@/lib/upload";
import { formatBytes, formatDateTime } from "@/lib/utils";

type FileListProps = {
  folders: FolderRead[];
  files: FileRead[];
  currentPath: Pick<FolderRead, "id" | "name">[];
  onGoUp: () => void;
  onNavigatePath: (index: number) => void;
  onOpenFolder: (folder: FolderRead) => void;
  onRefresh: () => void;
  loading?: boolean;
};

export function FileList({
  folders,
  files,
  currentPath,
  onGoUp,
  onNavigatePath,
  onOpenFolder,
  onRefresh,
  loading,
}: FileListProps) {
  const totalItems = folders.length + files.length;
  const showSkeleton = loading && totalItems === 0;

  return (
    <Card>
      <CardHeader className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-col gap-1.5">
          <CardTitle className="flex items-center gap-2">
            Мой диск
            <Badge variant="secondary">{totalItems}</Badge>
          </CardTitle>
          <CardDescription>
            Папки, файлы и действия в текущей директории.
          </CardDescription>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={onGoUp}
            disabled={loading || currentPath.length === 0}
          >
            <ArrowUp data-icon="inline-start" />
            Вверх
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={onRefresh}
            disabled={loading}
          >
            {loading ? (
              <Spinner data-icon="inline-start" />
            ) : (
              <RefreshCw data-icon="inline-start" />
            )}
            Обновить
          </Button>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <FolderBreadcrumb path={currentPath} onNavigate={onNavigatePath} />
        {showSkeleton ? (
          <FileTableSkeleton />
        ) : totalItems === 0 ? (
          <Empty className="border">
            <EmptyHeader>
              <EmptyMedia variant="icon">
                <FolderOpen />
              </EmptyMedia>
              <EmptyTitle>
                {currentPath.length > 0 ? "Папка пуста" : "Диск пуст"}
              </EmptyTitle>
              <EmptyDescription>
                Создайте папку или загрузите файл.
              </EmptyDescription>
            </EmptyHeader>
          </Empty>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Название</TableHead>
                <TableHead className="hidden md:table-cell">Размер</TableHead>
                <TableHead className="hidden lg:table-cell">Версия</TableHead>
                <TableHead className="hidden lg:table-cell">Создан</TableHead>
                <TableHead>Статус</TableHead>
                <TableHead className="text-right">Действия</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {folders.map((folder) => (
                <FolderRow
                  key={folder.id}
                  folder={folder}
                  onOpen={onOpenFolder}
                />
              ))}
              {files.map((file) => (
                <FileRow key={file.id} file={file} onChanged={onRefresh} />
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}

function FolderBreadcrumb({
  path,
  onNavigate,
}: {
  path: Pick<FolderRead, "id" | "name">[];
  onNavigate: (index: number) => void;
}) {
  return (
    <div className="flex min-h-10 flex-wrap items-center gap-1 rounded-md border px-2 py-1">
      <Button variant="ghost" size="sm" onClick={() => onNavigate(-1)}>
        <Home data-icon="inline-start" />
        Мой диск
      </Button>
      {path.map((folder, index) => (
        <Fragment key={folder.id}>
          <ChevronRight className="text-muted-foreground" />
          <Button variant="ghost" size="sm" onClick={() => onNavigate(index)}>
            {folder.name}
          </Button>
        </Fragment>
      ))}
    </div>
  );
}

function FolderRow({
  folder,
  onOpen,
}: {
  folder: FolderRead;
  onOpen: (folder: FolderRead) => void;
}) {
  return (
    <TableRow className="cursor-pointer" onDoubleClick={() => onOpen(folder)}>
      <TableCell>
        <div className="flex items-center gap-3">
          <span className="flex size-9 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
            <Folder />
          </span>
          <div className="min-w-0">
            <div className="truncate font-medium">{folder.name}</div>
            <div className="text-xs text-muted-foreground md:hidden">
              Папка
            </div>
          </div>
        </div>
      </TableCell>
      <TableCell className="hidden md:table-cell">—</TableCell>
      <TableCell className="hidden lg:table-cell">—</TableCell>
      <TableCell className="hidden lg:table-cell">
        {formatDateTime(folder.created_at)}
      </TableCell>
      <TableCell>
        <Badge variant="outline">Папка</Badge>
      </TableCell>
      <TableCell>
        <div className="flex justify-end">
          <Button variant="outline" size="sm" onClick={() => onOpen(folder)}>
            <FolderOpen data-icon="inline-start" />
            Открыть
          </Button>
        </div>
      </TableCell>
    </TableRow>
  );
}

function FileRow({
  file,
  onChanged,
}: {
  file: FileRead;
  onChanged: () => void;
}) {
  const versionInputRef = useRef<HTMLInputElement>(null);
  const [versionPending, setVersionPending] = useState(false);

  async function onDownload() {
    try {
      const payload = await api<{ url: string; expires_in_seconds: number }>(
        `/files/${file.id}/download-url`
      );
      window.location.href = payload.url;
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Ошибка скачивания");
    }
  }

  async function onShare() {
    try {
      const payload = await api<ShareLinkRead>("/shares/", {
        method: "POST",
        body: JSON.stringify({ file_id: file.id }),
      });
      const url = `${window.location.origin}/share/${payload.token}`;
      await navigator.clipboard.writeText(url);
      toast.success("Публичная ссылка скопирована");
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Ошибка создания ссылки"
      );
    }
  }

  function onVersionPick() {
    versionInputRef.current?.click();
  }

  async function onVersionChange(event: ChangeEvent<HTMLInputElement>) {
    const versionFile = event.target.files?.[0];
    if (!versionFile) return;
    setVersionPending(true);
    try {
      await uploadLargeFile(versionFile, {
        initiatePath: `/files/${file.id}/versions/uploads`,
        omitFilename: true,
      });
      toast.success("Новая версия загружена");
      onChanged();
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Ошибка новой версии"
      );
    } finally {
      setVersionPending(false);
      if (versionInputRef.current) versionInputRef.current.value = "";
    }
  }

  return (
    <TableRow>
      <TableCell>
        <div className="flex items-center gap-3">
          <span className="flex size-9 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
            <FileIcon />
          </span>
          <div className="min-w-0">
            <div className="truncate font-medium">{file.name}</div>
            <div className="text-xs text-muted-foreground md:hidden">
              {formatBytes(file.size_bytes)} · v{file.current_version_number}
            </div>
          </div>
        </div>
      </TableCell>
      <TableCell className="hidden md:table-cell">
        {formatBytes(file.size_bytes)}
      </TableCell>
      <TableCell className="hidden lg:table-cell">
        v{file.current_version_number}
      </TableCell>
      <TableCell className="hidden lg:table-cell">
        {formatDateTime(file.created_at)}
      </TableCell>
      <TableCell>
        <StatusBadge status={file.status} />
      </TableCell>
      <TableCell>
        <div className="flex flex-col gap-2 sm:flex-row sm:justify-end">
          <Button variant="outline" size="sm" onClick={onDownload}>
            <Download data-icon="inline-start" />
            Скачать
          </Button>
          <Button variant="outline" size="sm" onClick={onShare}>
            <LinkIcon data-icon="inline-start" />
            Ссылка
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={onVersionPick}
            disabled={versionPending}
          >
            {versionPending ? (
              <Spinner data-icon="inline-start" />
            ) : (
              <History data-icon="inline-start" />
            )}
            {versionPending ? "Загрузка..." : "Новая версия"}
          </Button>
          <input
            ref={versionInputRef}
            type="file"
            className="hidden"
            aria-hidden="true"
            tabIndex={-1}
            onChange={onVersionChange}
          />
        </div>
      </TableCell>
    </TableRow>
  );
}

function FileTableSkeleton() {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Название</TableHead>
          <TableHead className="hidden md:table-cell">Размер</TableHead>
          <TableHead className="hidden lg:table-cell">Версия</TableHead>
          <TableHead className="hidden lg:table-cell">Создан</TableHead>
          <TableHead>Статус</TableHead>
          <TableHead className="text-right">Действия</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {Array.from({ length: 4 }).map((_, index) => (
          <TableRow key={index}>
            <TableCell>
              <div className="flex items-center gap-3">
                <Skeleton className="size-9" />
                <div className="flex min-w-0 flex-1 flex-col gap-2">
                  <Skeleton className="h-4 w-48 max-w-full" />
                  <Skeleton className="h-3 w-28 md:hidden" />
                </div>
              </div>
            </TableCell>
            <TableCell className="hidden md:table-cell">
              <Skeleton className="h-4 w-16" />
            </TableCell>
            <TableCell className="hidden lg:table-cell">
              <Skeleton className="h-4 w-10" />
            </TableCell>
            <TableCell className="hidden lg:table-cell">
              <Skeleton className="h-4 w-28" />
            </TableCell>
            <TableCell>
              <Skeleton className="h-5 w-20" />
            </TableCell>
            <TableCell>
              <div className="flex justify-end">
                <Skeleton className="h-8 w-32" />
              </div>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function StatusBadge({ status }: { status: string }) {
  return <Badge variant={statusVariant(status)}>{statusLabel(status)}</Badge>;
}

function statusVariant(
  status: string
): "default" | "secondary" | "destructive" | "outline" {
  switch (status) {
    case "ready":
      return "secondary";
    case "failed":
    case "deleted":
      return "destructive";
    case "uploading":
      return "outline";
    default:
      return "outline";
  }
}

function statusLabel(status: string): string {
  switch (status) {
    case "ready":
      return "Готов";
    case "uploading":
      return "Загрузка";
    case "failed":
      return "Ошибка";
    case "deleted":
      return "Удалён";
    default:
      return status;
  }
}
