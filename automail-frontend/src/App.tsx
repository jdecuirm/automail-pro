import { createBrowserRouter, RouterProvider } from "react-router-dom";
import Layout from "@/routes/Layout";
import Dashboard from "@/routes/Dashboard";
import CampaignList from "@/routes/Campaigns/List";
import CampaignCreate from "@/routes/Campaigns/Create";
import CampaignDetail from "@/routes/Campaigns/Detail";
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
      { path: "settings/gmail", element: <SettingsGmail /> },
      { path: "settings/account", element: <SettingsAccount /> },
      { path: "*", element: <NotFound /> },
    ],
  },
]);

export default function App() {
  return <RouterProvider router={router} />;
}
