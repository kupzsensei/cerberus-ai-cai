import { createBrowserRouter } from "react-router-dom";
import App from "./App";
import Chatbot from "./pages/chat-bot/index.jsx"; // Corrected import path
import UploadPage from "./pages/pdf-professor/analyze-pdf";
import StatusPage from "./pages/pdf-professor/StatusPage";
import ResultPage from "./pages/pdf-professor/ResultPage";
import ResearchPage from "./pages/research";
import ResearchListPage from "./pages/research/list";
import ResearchDetailPage from "./pages/research/detail";
import InvestigatePage from "./pages/investigate";
import InvestigationListPage from "./pages/investigate/list";
import InvestigationDetailPage from "./pages/investigate/detail";
import ThreatsAndRisksPage from "./pages/threats-and-risks";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
    children: [
      {
        path: "",
        element: <Chatbot />,
      },
      {
        path: "/upload-pdf",
        element: <UploadPage />,
      },
      {
        path: "/task-status",
        element: <StatusPage />,
      },
      {
        path: "/task-status/:taskId",
        element: <ResultPage />,
      },
      {
        path: "/threats-and-risks",
        element: <ThreatsAndRisksPage />,
      },
      {
        path: "/research/list",
        element: <ResearchListPage />,
      },
      {
        path: "/research/:researchId",
        element: <ResearchDetailPage />,
      },
      {
        path: "/investigate",
        element: <InvestigatePage />,
      },
      {
        path: "/investigate/list",
        element: <InvestigationListPage />,
      },
      {
        path: "/investigate/:investigationId",
        element: <InvestigationDetailPage />,
      },
    ],
  },
]);
