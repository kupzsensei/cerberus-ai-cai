import { createBrowserRouter } from "react-router-dom";
import App from "./App";
import Chatbot from "./pages/chat-bot";
import UploadPage from "./pages/pdf-professor/analyze-pdf";
import StatusPage from "./pages/pdf-professor/StatusPage";
import ResultPage from "./pages/pdf-professor/ResultPage";

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
    ],
  },
]);
