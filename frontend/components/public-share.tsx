"use client";

import { useState } from "react";
import { Download } from "lucide-react";
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
import { Spinner } from "@/components/ui/spinner";

type PublicShareProps = {
  token: string;
};

export function PublicShare({ token }: PublicShareProps) {
  const [pending, setPending] = useState(false);
  const [statusText, setStatusText] = useState<string | null>(null);

  async function onDownload() {
    setPending(true);
    setStatusText("Подготовка ссылки...");
    try {
      const response = await fetch(`/api/public/${token}`);
      const text = await response.text();
      const payload = text ? JSON.parse(text) : null;
      if (!response.ok) {
        const detail = payload?.detail ?? "Ссылка недоступна";
        setStatusText(detail);
        toast.error(detail);
        return;
      }
      setStatusText("Ссылка готова, скачивание...");
      window.location.href = payload.url;
    } catch (error) {
      const message = error instanceof Error ? error.message : "Ошибка";
      setStatusText(message);
      toast.error(message);
    } finally {
      setPending(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardDescription>Gosling Drive</CardDescription>
        <CardTitle>Публичная ссылка</CardTitle>
        <CardDescription>Скачивание файла по одноразовой ссылке</CardDescription>
      </CardHeader>
      <CardContent>
        <Alert>
          <Download />
          <AlertTitle>Файл готов к скачиванию</AlertTitle>
          <AlertDescription>
            Нажмите кнопку ниже, чтобы получить временную ссылку.
          </AlertDescription>
        </Alert>
      </CardContent>
      <CardFooter className="flex flex-col items-stretch gap-4">
        <Button
          onClick={onDownload}
          disabled={pending}
          className="w-full"
          size="lg"
        >
          {pending ? (
            <Spinner data-icon="inline-start" />
          ) : (
            <Download data-icon="inline-start" />
          )}
          {pending ? "Готовим..." : "Скачать файл"}
        </Button>
        {statusText ? (
          <Alert>
            <Download />
            <AlertTitle>Статус</AlertTitle>
            <AlertDescription>{statusText}</AlertDescription>
          </Alert>
        ) : null}
      </CardFooter>
    </Card>
  );
}
