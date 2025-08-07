import { Outlet } from "react-router-dom";
import Sidebar from "./components/sidebar";
import { useState, useEffect } from "react";
import AIServerModal from "./components/AIServerModal";
import { getOllamaServers } from "./api/apiService";

function App() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  useEffect(() => {
    console.log("isModalOpen changed to:", isModalOpen);
  }, [isModalOpen]);
  const [ollamaServers, setOllamaServers] = useState([]);
  const [selectedOllamaServer, setSelectedOllamaServer] = useState(null);
  const [selectedModel, setSelectedModel] = useState(''); // Add selectedModel state

  useEffect(() => {
    const fetchServers = async () => {
      try {
        const servers = await getOllamaServers();
        setOllamaServers(servers);
        if (servers.length > 0) {
          setSelectedOllamaServer(servers[0]); // Select the first server by default
        }
      } catch (err) {
        console.error("Failed to fetch Ollama servers:", err);
      }
    };
    fetchServers();
  }, []);

  const handleServerSelected = (server) => {
    setSelectedOllamaServer(server);
  };

  return (
    <main className="w-screen h-screen flex bg-black">
      <Sidebar 
        ollamaServers={ollamaServers}
        selectedOllamaServer={selectedOllamaServer}
        setSelectedOllamaServer={setSelectedOllamaServer}
        setIsModalOpen={setIsModalOpen}
        selectedModel={selectedModel} // Pass selectedModel
        setSelectedModel={setSelectedModel} // Pass setSelectedModel
      />
      <section className="flex-1 flex flex-col items-center min-w-0 overflow-auto p-5">
        <Outlet context={{ selectedOllamaServer, selectedModel }} />
      </section>
      <AIServerModal 
        isOpen={isModalOpen} 
        onClose={() => setIsModalOpen(false)} 
        onServerSelected={handleServerSelected}
      />
    </main>
  );
}

export default App;

