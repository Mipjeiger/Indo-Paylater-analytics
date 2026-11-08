import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "react-router-dom";
import { router } from "./router";

const queryClient = new QueryClient({ defaultOptions: { queries: { staleTime: 30_000, refetchOnWindowFocus: false } } });

export function AppProviders(): ReactNode {
  return <QueryClientProvider client={queryClient}><RouterProvider router={router} /></QueryClientProvider>;
}
