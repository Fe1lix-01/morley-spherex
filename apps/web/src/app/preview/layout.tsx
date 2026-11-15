import type { ReactNode } from "react";
import Providers from "@/components/ui/Providers";

export const metadata = {
  title: "ÉTER · Visor espectral",
};

export default function PreviewLayout({ children }: { children: ReactNode }) {
  return <Providers>{children}</Providers>;
}