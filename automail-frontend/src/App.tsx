import { lazy, Suspense } from "react";
import {
  createBrowserRouter,
  Navigate,
  RouterProvider,
} from "react-router-dom";
import Layout from "@/routes/Layout";
import NotFound from "@/routes/NotFound";
import { RouteLoadingSkeleton } from "@/components/common/RouteLoadingSkeleton";

// errorElement cannot be lazy — it handles errors including lazy-load failures.
// Layout is not lazy — it's always rendered and wraps everything.
const Dashboard = lazy(() => import("@/routes/Dashboard"));
const CampaignList = lazy(() => import("@/routes/Campaigns/List"));
const CampaignCreate = lazy(() => import("@/routes/Campaigns/Create"));
const CampaignDetail = lazy(() => import("@/routes/Campaigns/Detail"));
const SettingsLayout = lazy(() => import("@/routes/Settings/SettingsLayout"));
const SettingsAccount = lazy(() => import("@/routes/Settings/Account"));
const SettingsGmail = lazy(() => import("@/routes/Settings/Gmail"));

const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout />,
    errorElement: <NotFound />,
    children: [
      {
        index: true,
        element: (
          <Suspense fallback={<RouteLoadingSkeleton />}>
            <Dashboard />
          </Suspense>
        ),
      },
      {
        path: "campaigns",
        element: (
          <Suspense fallback={<RouteLoadingSkeleton />}>
            <CampaignList />
          </Suspense>
        ),
      },
      {
        path: "campaigns/new",
        element: (
          <Suspense fallback={<RouteLoadingSkeleton />}>
            <CampaignCreate />
          </Suspense>
        ),
      },
      {
        path: "campaigns/:id",
        element: (
          <Suspense fallback={<RouteLoadingSkeleton />}>
            <CampaignDetail />
          </Suspense>
        ),
      },
      {
        path: "settings",
        element: (
          <Suspense fallback={<RouteLoadingSkeleton />}>
            <SettingsLayout />
          </Suspense>
        ),
        children: [
          { index: true, element: <Navigate to="account" replace /> },
          {
            path: "account",
            element: (
              <Suspense fallback={<RouteLoadingSkeleton />}>
                <SettingsAccount />
              </Suspense>
            ),
          },
          {
            path: "gmail",
            element: (
              <Suspense fallback={<RouteLoadingSkeleton />}>
                <SettingsGmail />
              </Suspense>
            ),
          },
        ],
      },
      { path: "*", element: <NotFound /> },
    ],
  },
]);

export default function App() {
  return <RouterProvider router={router} />;
}
