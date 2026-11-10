import { useQuery } from "@tanstack/react-query";
import { Activity, CheckCircle2, Server, TerminalSquare } from "lucide-react";
import { PageHeader } from "../components/ui/PageHeader";
import { MetricCard } from "../components/ui/MetricCard";
import { getHealth, getMetrics } from "../services/monitoring-service";

export function MonitoringPage() {
  const health = useQuery({
    queryKey: ["service-health"],
    queryFn: ({ signal }) => getHealth(signal),
    retry: false,
    refetchInterval: 30_000,
  });
  const metrics = useQuery({
    queryKey: ["prometheus-metrics"],
    queryFn: ({ signal }) => getMetrics(signal),
    retry: false,
    refetchInterval: 30_000,
  });

  return (
    <>
      <PageHeader
        eyebrow="Operational observability"
        title="Monitoring"
        description="Live service status from the controlled FastAPI integration boundary."
      />
      <div className="metric-grid monitoring-metric-grid">
        <MetricCard
          label="API availability"
          value={health.isSuccess ? "Healthy" : health.isLoading ? "Checking" : "Unavailable"}
          detail={health.data?.status ?? health.error?.message}
          icon={<Server size={19} />}
          tone={health.isSuccess ? "green" : "red"}
        />
        <MetricCard
          label="Metrics endpoint"
          value={metrics.isSuccess ? "Connected" : metrics.isLoading ? "Checking" : "Unavailable"}
          detail={metrics.isSuccess ? "Prometheus text received" : "No metrics response"}
          icon={<Activity size={19} />}
          tone={metrics.isSuccess ? "green" : "amber"}
        />
        <MetricCard
          label="Prediction boundary"
          value="FastAPI"
          detail="Browser does not access MLflow directly"
          icon={<TerminalSquare size={19} />}
          tone="blue"
        />
      </div>
      <div className="panel-grid">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">Health check</span>
              <h3>Backend service status</h3>
            </div>
            <CheckCircle2 className={health.isSuccess ? "text-success" : "text-amber"} size={19} />
          </div>
          <p className="panel-copy">
            {health.isSuccess
              ? "The FastAPI health endpoint responded successfully."
              : health.isLoading
                ? "Waiting for a response from FastAPI."
                : health.error?.message ?? "The health endpoint did not respond."}
          </p>
        </section>
        <section className="panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">Controlled integration</span>
              <h3>Prometheus metrics</h3>
            </div>
          </div>
          <p className="panel-copy">
            {metrics.isSuccess
              ? "Metrics are available through FastAPI for operational integrations."
              : metrics.isLoading
                ? "Waiting for the metrics endpoint."
                : metrics.error?.message ?? "Metrics are currently unavailable."}
          </p>
        </section>
      </div>
    </>
  );
}
