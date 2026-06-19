import {
  createBrowserRouter,
  Navigate,
  RouterProvider,
} from "react-router-dom";
import Layout from "@/routes/Layout";
import Dashboard from "@/routes/Dashboard";
import CampaignList from "@/routes/Campaigns/List";
import CampaignCreate from "@/routes/Campaigns/Create";
import CampaignDetail from "@/routes/Campaigns/Detail";
import SettingsLayout from "@/routes/Settings/SettingsLayout";
import SettingsGmail from "@/routes/Settings/Gmail";
import SettingsAccount from "@/routes/Settings/Account";
import NotFound from "@/routes/NotFound";

const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout />,
    errorElement: <NotFound />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: "campaigns", element: <CampaignList /> },
      { path: "campaigns/new", element: <CampaignCreate /> },
      { path: "campaigns/:id", element: <CampaignDetail /> },
      {
        path: "settings",
        element: <SettingsLayout />,
        children: [
          { index: true, element: <Navigate to="account" replace /> },
          { path: "account", element: <SettingsAccount /> },
          { path: "gmail", element: <SettingsGmail /> },
        ],
      },
      { path: "*", element: <NotFound /> },
    ],
  },
]);

export default function App() {
  return <RouterProvider router={router} />;
}
