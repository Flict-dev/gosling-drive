"use client";

import { type FormEvent, useState } from "react";
import { FolderPlus } from "lucide-react";
import { toast } from "sonner";

import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";

type FolderCardProps = {
  onCreated: () => void;
};

export function FolderCard({ onCreated }: FolderCardProps) {
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    const form = event.currentTarget;
    const formData = new FormData(form);
    try {
      await api("/folders/", {
        method: "POST",
        body: JSON.stringify(Object.fromEntries(formData)),
      });
      toast.success("Папка создана");
      form.reset();
      onCreated();
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Ошибка создания папки"
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Папка</CardTitle>
        <CardDescription>Создать новую папку в корне</CardDescription>
      </CardHeader>
      <form onSubmit={onSubmit}>
        <CardContent>
          <FieldGroup className="gap-4">
            <Field data-disabled={pending ? true : undefined}>
              <FieldLabel htmlFor="folder-name">Название</FieldLabel>
              <Input
                id="folder-name"
                name="name"
                type="text"
                disabled={pending}
                required
              />
            </Field>
          </FieldGroup>
        </CardContent>
        <CardFooter>
          <Button type="submit" disabled={pending} className="w-full">
            {pending ? (
              <Spinner data-icon="inline-start" />
            ) : (
              <FolderPlus data-icon="inline-start" />
            )}
            {pending ? "Создаём..." : "Создать"}
          </Button>
        </CardFooter>
      </form>
    </Card>
  );
}
