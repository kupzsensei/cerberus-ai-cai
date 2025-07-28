import logo from "../assets/cerberus-logo.png";
import { NavLink } from "react-router-dom";
import { FaCog } from 'react-icons/fa'; // Import a gear icon
import { useEffect, useState } from "react";
import { getOllamaModels } from "../api/apiService";

export default function Sidebar({ ollamaServers, selectedOllamaServer, setSelectedOllamaServer, setIsModalOpen, selectedModel, setSelectedModel }) {
    const [models, setModels] = useState([]);
    const [isLoadingModels, setIsLoadingModels] = useState(false);
    const [modelError, setModelError] = useState(null);

    useEffect(() => {
        const fetchModels = async () => {
            if (selectedOllamaServer) {
                setIsLoadingModels(true);
                setModelError(null);
                try {
                    const fetchedModels = await getOllamaModels(selectedOllamaServer.url);
                    setModels(fetchedModels);
                    if (fetchedModels.length > 0) {
                        setSelectedModel(fetchedModels[0]); // Select the first model by default
                    } else {
                        setSelectedModel('');
                    }
                } catch (err) {
                    console.error("Failed to fetch models:", err);
                    setModelError("Failed to load models from selected server.");
                    setModels([]);
                    setSelectedModel('');
                } finally {
                    setIsLoadingModels(false);
                }
            }
        };
        fetchModels();
    }, [selectedOllamaServer, setSelectedModel]);

    const handleServerChange = (e) => {
        const serverName = e.target.value;
        const server = ollamaServers.find(s => s.name === serverName);
        if (server) {
            setSelectedOllamaServer(server);
        }
    };

    const handleModelChange = (e) => {
        setSelectedModel(e.target.value);
    };

    return (
        <section className="flex flex-col gap-5 p-5 border-green-500 border-r min-w-[300px]">
            <div className="flex items-end gap-2 border-green-500 border-b pb-5">
                <img
                    className="h-[50px] drop-shadow-green-600 drop-shadow-md"
                    src={logo}
                    alt=""
                />

                <div>
                    <h1 className="text-green-500 font-bold text-xl  drop-shadow-green-600 drop-shadow-md ">
                        Cerberus AI - Cai
                    </h1>
                    <p className="text-red-700 text-xs  drop-shadow-red-600 drop-shadow-md ">
                         {selectedOllamaServer ? `${selectedOllamaServer.name} (${selectedOllamaServer.url})` : 'Ollama'}
                        <FaCog className="inline-block ml-2 cursor-pointer" onClick={() => {
                            console.log("Cog icon clicked, setting isModalOpen to true");
                            setIsModalOpen(true);
                        }} />
                    </p>
                </div>
            </div>

            {/* navigation */}
            <div className="flex flex-col gap-5 flex-1 min-h-0">
                <NavLink to={'/'} className={({ isActive }) => isActive ?
                    "text-green-500 font-bold text-xl  drop-shadow-green-600 drop-shadow-md border-green-500 border  hover:border p-2"
                    : "text-green-700 hover:text-green-500 font-bold   drop-shadow-green-600 drop-shadow-md border-green-500 hover:border p-2"}>
                    Chatbot
                </NavLink>

                <div className="flex flex-col">
                    <span className="text-green-800  text-xs  drop-shadow-green-600 drop-shadow-md border-green-500 ">
                        PDFProfessor
                    </span>
                    <NavLink to={'/upload-pdf'} className={({ isActive }) => isActive ?
                        "text-green-500 font-bold text-xl  drop-shadow-green-600 drop-shadow-md border-green-500 border  hover:border p-2"
                        : "text-green-700 hover:text-green-500 font-bold   drop-shadow-green-600 drop-shadow-md border-green-500 hover:border p-2"}>
                        Analyze PDF
                    </NavLink>
                    <NavLink to={'/task-status'} className={({ isActive }) => isActive ?
                        "text-green-500 font-bold text-xl  drop-shadow-green-600 drop-shadow-md border-green-500 border  hover:border p-2"
                        : "text-green-700 hover:text-green-500 font-bold   drop-shadow-green-600 drop-shadow-md border-green-500 hover:border p-2"}>
                        Task Status
                    </NavLink>
                </div>
                <div className="flex flex-col">
                    <span className="text-green-800  text-xs  drop-shadow-green-600 drop-shadow-md border-green-500 ">
                        Threats and Risks
                    </span>
                    <NavLink to={'/threats-and-risks'} end className={({ isActive }) => isActive ?
                        "text-green-500 font-bold text-xl  drop-shadow-green-600 drop-shadow-md border-green-500 border  hover:border p-2"
                        : "text-green-700 hover:text-green-500 font-bold   drop-shadow-green-600 drop-shadow-md border-green-500 hover:border p-2"}>
                        Cybersecurity Research
                    </NavLink>
                    <NavLink to={'/research/list'} className={({ isActive }) => isActive ?
                        "text-green-500 font-bold text-xl  drop-shadow-green-600 drop-shadow-md border-green-500 border  hover:border p-2"
                        : "text-green-700 hover:text-green-500 font-bold   drop-shadow-green-600 drop-shadow-md border-green-500 hover:border p-2"}>
                        Research List
                    </NavLink>
                </div>
                <div className="flex flex-col">
                    <span className="text-green-800  text-xs  drop-shadow-green-600 drop-shadow-md border-green-500 ">
                        Investigation
                    </span>
                    <NavLink to={'/investigate'} end  className={({ isActive }) => isActive ?
                        "text-green-500 font-bold text-xl  drop-shadow-green-600 drop-shadow-md border-green-500 border  hover:border p-2"
                        : "text-green-700 hover:text-green-500 font-bold   drop-shadow-green-600 drop-shadow-md border-green-500 hover:border p-2"}>
                        Investigate
                    </NavLink>
                    <NavLink to={'/investigate/list'} end className={({ isActive }) => isActive ?
                        "text-green-500 font-bold text-xl  drop-shadow-green-600 drop-shadow-md border-green-500 border  hover:border p-2"
                        : "text-green-700 hover:text-green-500 font-bold   drop-shadow-green-600 drop-shadow-md border-green-500 hover:border p-2"}>
                        Investigation List
                    </NavLink>
                </div>
                <span className="text-green-800 font-bold text-xl  drop-shadow-green-600 drop-shadow-md border-green-500 hover:border p-2">
                    Coming Soon...
                </span>
            </div>

            {/* footer */}
            <div className="text-green-800 border-dashed flex flex-col border-green-500 ">
                <p className="text-xs text-red-800  drop-shadow-red-600 drop-shadow-md">
                    current server
                </p>
                <select className="p-2 font-bold border-green-500 border" value={selectedOllamaServer?.name || ''} onChange={handleServerChange}>
                    {ollamaServers.length === 0 ? (
                        <option value="">No servers configured</option>
                    ) : (
                        ollamaServers.map(server => (
                            <option key={server.name} value={server.name}>
                                {server.name}
                            </option>
                        ))
                    )}
                </select>

                <p className="text-xs text-red-800  drop-shadow-red-600 drop-shadow-md mt-4">
                    current model
                </p>
                <select 
                    className="p-2 font-bold border-green-500 border"
                    value={selectedModel}
                    onChange={handleModelChange}
                    disabled={isLoadingModels || modelError || models.length === 0}
                >
                    {isLoadingModels && <option>Loading models...</option>}
                    {modelError && <option>Error loading models</option>}
                    {!isLoadingModels && !modelError && models.length === 0 && <option>No models available</option>}
                    {models.map(modelName => (
                        <option key={modelName} value={modelName}>
                            {modelName}
                        </option>
                    ))}
                </select>
            </div>
        </section>
    );
}
