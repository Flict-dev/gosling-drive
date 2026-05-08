"use client";

import { type FormEvent, useRef, useState } from "react";
import { Upload } from "lucide-react";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Spinner } from "@/components/ui/spinner";
import { uploadLargeFile } from "@/lib/upload";

type UploadCardProps = {
  onUploaded: () => void;
};

export function UploadCard({ onUploaded }: UploadCardProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [pending, setPending] = useState(false);
  const [progress, setProgress] = useState(0);
  const [statusText, setStatusText] = useState<string | null>(null);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const file = inputRef.current?.files?.[0];
    if (!file) {
      toast.error("Выберите файл");
      return;
    }
    setPending(true);
    setProgress(0);
    setStatusText("Создание сессии...");
    try {
      await uploadLargeFile(file, {
        onProgress: (percent) => {
          setProgress(percent);
          setStatusText(`${percent}%`);
        },
      });
      setStatusText("Готово");
      toast.success("Файл загружен");
      if (inputRef.current) inputRef.current.value = "";
      onUploaded();
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Ошибка загрузки";
      setStatusText(message);
      toast.error(message);
    } finally {
      setPending(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Загрузка</CardTitle>
        <CardDescription>
          Файл уходит напрямую в MinIO multipart-частями
        </CardDescription>
      </CardHeader>
      <form onSubmit={onSubmit}>
        <CardContent>
          <FieldGroup className="gap-4">
            <Field data-disabled={pending ? true : undefined}>
              <FieldLabel htmlFor="file">Файл</FieldLabel>
              <Input
                id="file"
                name="file"
                type="file"
                ref={inputRef}
                disabled={pending}
                required
              />
              <FieldDescription>
                Большие файлы загружаются multipart-частями.
              </FieldDescription>
            </Field>
          </FieldGroup>
        </CardContent>
        <CardFooter className="flex flex-col items-stretch gap-4">
          <Button type="submit" disabled={pending} className="w-full">
            {pending ? (
              <Spinner data-icon="inline-start" />
            ) : (
              <Upload data-icon="inline-start" />
            )}
            {pending ? "Загружаем..." : "Загрузить"}
          </Button>
          {pending || progress > 0 ? (
            <Alert>
              <Upload />
              <AlertTitle>Статус загрузки</AlertTitle>
              <AlertDescription className="flex flex-col gap-2">
                <Progress value={progress} />
                {statusText ? <span>{statusText}</span> : null}
              </AlertDescription>
            </Alert>
          ) : null}
        </CardFooter>
      </form>
    </Card>
  );
}
