"use client";

import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";

import { Button } from "@/components/ui/button";
import { useMounted } from "@/hooks/use-mounted";

type Tema = "light" | "dark";

function temaResolvido(resolvedTheme: string | undefined): Tema | null {
  if (resolvedTheme === "light" || resolvedTheme === "dark") {
    return resolvedTheme;
  }
  return null;
}

export function ToggleTheme() {
  const { resolvedTheme, setTheme } = useTheme();
  const montado = useMounted();
  const tema = montado ? temaResolvido(resolvedTheme) : null;

  return (
    <Button
      type="button"
      variant="ghost"
      size="icon"
      className="ml-auto"
      aria-label="Alternar tema"
      onClick={() => {
        if (tema === null) {
          return;
        }
        setTheme(tema === "dark" ? "light" : "dark");
      }}
    >
      {tema === "dark" ? (
        <Moon />
      ) : tema === "light" ? (
        <Sun />
      ) : (
        <span className="size-4" aria-hidden="true" />
      )}
    </Button>
  );
}
