// @spec docs/BACKLOG.md#RG-013 | docs/BACKLOG.md#RG-012 | docs/DESIGN_SYSTEM_APP.md#architecture
// Routes : accueil public, quatre destinations réservées à une session ouverte.
import type { ReactNode } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth";
import { Skeleton } from "./components/ui/Skeleton";
import { Engines } from "./pages/Engines";
import { Home } from "./pages/Home";
import { Journal } from "./pages/Journal";
import { Policies } from "./pages/Policies";
import { Sandbox } from "./pages/Sandbox";

function Protected({ children }: { children: ReactNode }) {
  const { status } = useAuth();
  if (status === "checking") return <Skeleton lines={4} />;
  if (status === "anonymous") return <Navigate to="/" replace />;
  return <>{children}</>;
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/journal" element={<Protected><Journal /></Protected>} />
      <Route path="/bac-a-sable" element={<Protected><Sandbox /></Protected>} />
      <Route path="/politiques" element={<Protected><Policies /></Protected>} />
      <Route path="/moteurs" element={<Protected><Engines /></Protected>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  );
}
