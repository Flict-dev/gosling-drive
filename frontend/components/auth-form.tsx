"use client";

import { type FormEvent, useState } from "react";
import { toast } from "sonner";

import { api, type LoginResponse } from "@/lib/api";
import { setToken } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
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
import { Spinner } from "@/components/ui/spinner";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

type AuthFormProps = {
  onAuthenticated: () => Promise<void> | void;
};

export function AuthForm({ onAuthenticated }: AuthFormProps) {
  const [loginPending, setLoginPending] = useState(false);
  const [registerPending, setRegisterPending] = useState(false);

  async function onLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoginPending(true);
    const formData = new FormData(event.currentTarget);
    try {
      const payload = await api<LoginResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify(Object.fromEntries(formData)),
      });
      setToken(payload.access_token);
      toast.success("Вход выполнен");
      await onAuthenticated();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Ошибка входа");
    } finally {
      setLoginPending(false);
    }
  }

  async function onRegister(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setRegisterPending(true);
    const form = event.currentTarget;
    const formData = new FormData(form);
    try {
      await api("/auth/register", {
        method: "POST",
        body: JSON.stringify(Object.fromEntries(formData)),
      });
      toast.success("Аккаунт создан, теперь войдите");
      form.reset();
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Ошибка регистрации"
      );
    } finally {
      setRegisterPending(false);
    }
  }

  return (
    <Card className="mx-auto w-full max-w-md">
      <CardHeader>
        <CardTitle>Gosling Drive</CardTitle>
        <CardDescription>
          Войдите в хранилище или создайте новый аккаунт.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="login" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="login">Вход</TabsTrigger>
            <TabsTrigger value="register">Регистрация</TabsTrigger>
          </TabsList>

          <TabsContent value="login">
            <form onSubmit={onLogin} className="flex flex-col gap-4 pt-2">
              <FieldGroup className="gap-4">
                <Field>
                  <FieldLabel htmlFor="login-email">Email</FieldLabel>
                  <Input
                    id="login-email"
                    name="email"
                    type="email"
                    autoComplete="email"
                    required
                  />
                </Field>
                <Field>
                  <FieldLabel htmlFor="login-password">Пароль</FieldLabel>
                  <Input
                    id="login-password"
                    name="password"
                    type="password"
                    autoComplete="current-password"
                    required
                  />
                </Field>
              </FieldGroup>
              <Button type="submit" className="w-full" disabled={loginPending}>
                {loginPending ? <Spinner data-icon="inline-start" /> : null}
                {loginPending ? "Входим..." : "Войти"}
              </Button>
            </form>
          </TabsContent>

          <TabsContent value="register">
            <form onSubmit={onRegister} className="flex flex-col gap-4 pt-2">
              <FieldGroup className="gap-4">
                <Field>
                  <FieldLabel htmlFor="register-name">Имя</FieldLabel>
                  <Input
                    id="register-name"
                    name="full_name"
                    type="text"
                    autoComplete="name"
                    required
                  />
                </Field>
                <Field>
                  <FieldLabel htmlFor="register-email">Email</FieldLabel>
                  <Input
                    id="register-email"
                    name="email"
                    type="email"
                    autoComplete="email"
                    required
                  />
                </Field>
                <Field>
                  <FieldLabel htmlFor="register-password">Пароль</FieldLabel>
                  <Input
                    id="register-password"
                    name="password"
                    type="password"
                    autoComplete="new-password"
                    minLength={8}
                    required
                  />
                  <FieldDescription>Минимум 8 символов.</FieldDescription>
                </Field>
              </FieldGroup>
              <Button
                type="submit"
                className="w-full"
                disabled={registerPending}
              >
                {registerPending ? <Spinner data-icon="inline-start" /> : null}
                {registerPending ? "Создаём..." : "Создать аккаунт"}
              </Button>
            </form>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
