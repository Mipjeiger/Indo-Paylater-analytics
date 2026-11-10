import { PageHeader } from "../components/ui/PageHeader";

type DomainPageProps = { title: string; description: string; endpoint: string; purpose: string };

export function DomainPage({ title, description, endpoint, purpose }: DomainPageProps) {
  return <><PageHeader eyebrow="PayLater Intelligence" title={title} description={description} /><section className="panel unavailable-panel"><div className="unavailable-icon">!</div><div><h3>Backend endpoint not available</h3><p>{purpose}</p><code>{endpoint}</code><p className="muted">The current FastAPI application does not register this endpoint. The frontend keeps the page empty rather than showing fabricated records.</p></div></section></>;
}
