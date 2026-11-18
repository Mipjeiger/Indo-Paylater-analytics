import { createBrowserRouter } from "react-router-dom";
import { AppShell } from "../components/layout/AppShell";
import { OverviewPage } from "../pages/OverviewPage";
import { RiskPage } from "../pages/RiskPage";
import { MonitoringPage } from "../pages/MonitoringPage";
import { AuditPage, BorrowersPage, DecisionsPage, ModelsPage, PortfolioPage } from "../pages/DataPages";

export const router = createBrowserRouter([{
  path: "/",
  element: <AppShell />,
  children: [
    { index: true, element: <OverviewPage /> },
    { path: "borrowers", element: <BorrowersPage /> },
    { path: "risk", element: <RiskPage /> },
    { path: "decisions", element: <DecisionsPage /> },
    { path: "portfolio", element: <PortfolioPage /> },
    { path: "models", element: <ModelsPage /> },
    { path: "monitoring", element: <MonitoringPage /> },
    { path: "audit", element: <AuditPage /> },
  ],
}]);
