import { createBrowserRouter } from "react-router-dom";
import { AppShell } from "../components/layout/AppShell";
import { DomainPage } from "../pages/DomainPage";
import { OverviewPage } from "../pages/OverviewPage";
import { RiskPage } from "../pages/RiskPage";

export const router = createBrowserRouter([{
  path: "/",
  element: <AppShell />,
  children: [
    { index: true, element: <OverviewPage /> },
    { path: "borrowers", element: <DomainPage title="Borrower intelligence" description="Investigate borrower profiles, financial indicators, and historical assessments." endpoint="GET /api/v1/borrowers" purpose="A server-side borrower directory and profile contract is required before displaying borrower records." /> },
    { path: "risk", element: <RiskPage /> },
    { path: "decisions", element: <DomainPage title="Decision management" description="Review recommendations and maintain an auditable decision workflow." endpoint="GET /api/v1/decisions" purpose="Decision queues and approval actions require verified backend authorization and audit endpoints." /> },
    { path: "portfolio", element: <DomainPage title="Portfolio analytics" description="Understand exposure, repayment performance, delinquency, and segmentation." endpoint="GET /api/v1/portfolio/summary" purpose="Portfolio calculations must be server-side and period-aware." /> },
    { path: "models", element: <DomainPage title="Model intelligence" description="Review production model versions, governance, and evaluation history." endpoint="GET /api/v1/models" purpose="Model registry metadata must be exposed through a controlled FastAPI boundary." /> },
    { path: "monitoring", element: <DomainPage title="Monitoring" description="Track API availability, model service health, latency, and drift." endpoint="GET /api/v1/monitoring/summary" purpose="The browser must not connect directly to Prometheus or internal infrastructure." /> },
    { path: "audit", element: <DomainPage title="Audit & governance" description="Trace assessments, decisions, actors, timestamps, and model versions." endpoint="GET /api/v1/audit/events" purpose="Audit records must come from immutable backend records and are not fabricated client-side." /> },
  ],
}]);
