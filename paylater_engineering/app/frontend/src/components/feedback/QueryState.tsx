import type { ReactNode } from "react";

type QueryStateProps = {
  isLoading: boolean;
  error: Error | null;
  children: ReactNode;
  empty?: boolean;
};

export function QueryState({ isLoading, error, children, empty }: QueryStateProps) {
  if (isLoading) return <div className="state-card">Loading verified data…</div>;
  if (error) return <div className="state-card state-error"><strong>Data unavailable</strong><span>{error.message}</span></div>;
  if (empty) return <div className="state-card">No records are available for this view.</div>;
  return children;
}
