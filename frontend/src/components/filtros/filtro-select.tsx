"use client";

import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

type Opcao = {
  value: string;
  label: string;
};

type FiltroSelectProps = {
  id: string;
  label: string;
  value: string;
  options: readonly Opcao[];
  onChange: (value: string) => void;
};

export function FiltroSelect({
  id,
  label,
  value,
  options,
  onChange,
}: FiltroSelectProps) {
  return (
    <div className="flex min-w-36 flex-1 basis-0 flex-col gap-1.5">
      <Label htmlFor={id} className="h-5 leading-5">
        {label}
      </Label>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger id={id} className="h-8 w-full">
          <SelectValue />
        </SelectTrigger>
        <SelectContent position="popper">
          {options.map((opcao) => (
            <SelectItem key={opcao.value} value={opcao.value}>
              {opcao.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
