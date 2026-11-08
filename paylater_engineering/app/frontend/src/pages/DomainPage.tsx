import { PageHeader } from "../components/ui/PageHeader";

type DomainPageProps = { title: string; description: string; endpoint: string; purpose: string };

export function DomainPage({ title, description, endpoint, purpose }: DomainPageProps) {
  return <><PageHeader eyebrow="PayLater Intelligence" title={title} description={description} /><section className="panel unavailable-panel"><div className="unavailable-icon">!</div><div><h3>Backend capability required</h3><p>{purpose}</p><code>{endpoint}</code><p className="muted">This screen will render verified records when the backend contract is available. It does not display fabricated data.</p></div></section></>;
}
