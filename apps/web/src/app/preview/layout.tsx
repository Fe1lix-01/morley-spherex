import type { ReactNode } from "react";
import Providers from "@/components/ui/Providers";
import ChatBot from "@/components/chat/ChatBot";

export const metadata = {
  title: "ÉTER · Visor espectral",
};

export default function PreviewLayout({ children }: { children: ReactNode }) {
  return <Providers>{children}<ChatBot /></Providers>;
}