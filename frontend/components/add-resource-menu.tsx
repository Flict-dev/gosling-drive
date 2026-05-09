"use client";

import { type ChangeEvent, type FormEvent, useRef, useState } from "react";
import { FileUp, FolderPlus, Plus } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { api } from "@/lib/api";
import { uploadLargeFile } from "@/lib/upload";

type AddResourceMenuProps = {
  folderId: string | null;
  folderName: string;
  onChanged: () => void | Promise<void>;
  disabled?: boolean;
};

export function AddResourceMenu({
  folderId,
  folderName,
  onChanged,
  disabled,
}: AddResourceMenuProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [folderDialogOpen, setFolderDialogOpen] = useState(false);
  const [uploadPending, setUploadPending] = useState(false);
  const [folderPending, setFolderPending] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

  const pending = uploadPending || folderPending;

  function onPickFile() {
    fileInputRef.current?.click();
  }

  async function onFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    setUploadPending(true);
    setUploadProgress(0);
    try {
      await uploadLargeFile(file, {
        folderId,
        onProgress: setUploadProgress,
      });
      toast.success("Файл загружен");
      await onChanged();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Ошибка загрузки");
    } finally {
      setUploadPending(false);
      setUploadProgress(0);
      event.currentTarget.value = "";
    }
  }

  async function onCreateFolder(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFolderPending(true);

    const form = event.currentTarget;
    const formData = new FormData(form);
    const payload: Record<string, unknown> = {
      name: String(formData.get("name") ?? ""),
    };
    if (folderId) {
      payload.parent_id = folderId;
    }

    try {
      await api("/folders/", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      toast.success("Папка создана");
      form.reset();
      setFolderDialogOpen(false);
      await onChanged();
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Ошибка создания папки"
      );
    } finally {
      setFolderPending(false);
    }
  }

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button size="sm" disabled={disabled || pending}>
            {uploadPending ? (
              <Spinner data-icon="inline-start" />
            ) : (
              <Plus data-icon="inline-start" />
            )}
            {uploadPending ? `Загрузка ${uploadProgress}%` : "Добавить"}
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-44">
          <DropdownMenuItem
            disabled={disabled || pending}
            onSelect={onPickFile}
          >
            <FileUp data-icon="inline-start" />
            Файл
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            disabled={disabled || pending}
            onSelect={() => setFolderDialogOpen(true)}
          >
            <FolderPlus data-icon="inline-start" />
            Папку
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        aria-hidden="true"
        tabIndex={-1}
        disabled={disabled || pending}
        onChange={onFileChange}
      />

      <Dialog
        open={folderDialogOpen}
        onOpenChange={(open) => {
          if (!folderPending) setFolderDialogOpen(open);
        }}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Новая папка</DialogTitle>
            <DialogDescription>
              Будет создана в: {folderName}
            </DialogDescription>
          </DialogHeader>
          <form className="flex flex-col gap-4" onSubmit={onCreateFolder}>
            <FieldGroup>
              <Field data-disabled={folderPending ? true : undefined}>
                <FieldLabel htmlFor="new-folder-name">Название</FieldLabel>
                <Input
                  id="new-folder-name"
                  name="name"
                  type="text"
                  disabled={folderPending}
                  autoFocus
                  required
                />
              </Field>
            </FieldGroup>
            <DialogFooter className="gap-2 sm:gap-2">
              <Button
                type="button"
                variant="outline"
                disabled={folderPending}
                onClick={() => setFolderDialogOpen(false)}
              >
                Отмена
              </Button>
              <Button type="submit" disabled={folderPending}>
                {folderPending ? (
                  <Spinner data-icon="inline-start" />
                ) : (
                  <FolderPlus data-icon="inline-start" />
                )}
                {folderPending ? "Создаём..." : "Создать"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </>
  );
}
