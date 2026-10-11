import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Route, Routes, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Navbar } from "../components/Navbar";
import { Footer } from "../components/Footer";
import { LandingPage }          from "../pages/LandingPage";
import { CampaignListPage }     from "../pages/CampaignListPage";
import { CampaignDetailPage }   from "../pages/CampaignDetailPage";
import { VerificationPage }     from "../pages/VerificationPage";
import { ResultsPage }          from "../pages/ResultsPage";
import { LoginPage }            from "../pages/LoginPage";
import { StaffAccessPage }      from "../pages/StaffAccessPage";
import { RegisterPage }         from "../pages/RegisterPage";
import { MyEntriesPage }        from "../pages/MyEntriesPage";
import { VendorDashboardPage }  from "../pages/VendorDashboardPage";
import { AdminDashboardPage }   from "../pages/AdminDashboardPage";
import { NotFoundPage }         from "../pages/NotFoundPage";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 30_000 } },
});

// Routes where we hide the standard Navbar/Footer (auth pages have their own layout)
const AUTH_PATHS = ["/login", "/register", "/staff/login", "/staff/setup"];

function Layout() {
  const { pathname } = useLocation();
  const { t } = useTranslation();
  const isAuth = AUTH_PATHS.some((p) => pathname.startsWith(p));
  const demoNotice = import.meta.env.VITE_PUBLIC_DEMO === "true" ? (
    <aside className="ad-demo-banner" role="note">{t("demo.notice")}</aside>
  ) : null;

  if (isAuth) {
    return (
      <>
        {demoNotice}
        <Routes>
          <Route path="/login"    element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/staff/login" element={<StaffAccessPage />} />
          <Route path="/staff/setup" element={<StaffAccessPage setup />} />
        </Routes>
      </>
    );
  }

  return (
    <>
      {demoNotice}
      <div style={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}>
        <Navbar />
        <main style={{ flex: 1 }}>
          <Routes>
            <Route path="/"                    element={<LandingPage />} />
            <Route path="/campaigns"           element={<CampaignListPage />} />
            <Route path="/campaigns/:id"       element={<CampaignDetailPage />} />
            <Route path="/verify"              element={<VerificationPage />} />
            <Route path="/verify/:drawId"      element={<VerificationPage />} />
            <Route path="/results"             element={<ResultsPage />} />
            <Route path="/my-entries"          element={<MyEntriesPage />} />
            <Route path="/vendor/*"            element={<VendorDashboardPage />} />
            <Route path="/admin/*"             element={<AdminDashboardPage />} />
            <Route path="*"                    element={<NotFoundPage />} />
          </Routes>
        </main>
        <Footer />
      </div>
    </>
  );
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Layout />
    </QueryClientProvider>
  );
}
