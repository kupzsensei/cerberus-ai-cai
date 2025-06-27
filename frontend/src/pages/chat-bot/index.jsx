import React, { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import * as pdfjsLib from "pdfjs-dist";
import * as mammoth from "mammoth";
import { useOutletContext } from "react-router-dom";
import { OLLAMA_BASE_URL } from "../../api";

pdfjsLib.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";

const extractTextFromPDF = async (file) => {
    const typedArray = new Uint8Array(await file.arrayBuffer());
    const pdf = await pdfjsLib.getDocument(typedArray).promise;

    let fullText = "";
    for (let i = 1; i <= pdf.numPages; i++) {
        const page = await pdf.getPage(i);
        const content = await page.getTextContent();
        const pageText = content.items.map((item) => item.str).join(" ");
        fullText += `\n\n${pageText}`;
    }

    return fullText;
};

const extractTextFromDocx = async (file) => {
    const arrayBuffer = await file.arrayBuffer();
    const result = await mammoth.extractRawText({ arrayBuffer });
    return result.value;
};

const availableModels = [
    "gemma3",
    "qwen3:8b",
    "deepseek-r1:latest",
    "mistral-nemo:12b",
];

const SendIcon = () => (
    <svg
        width="24"
        height="24"
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="text-white"
    >
        <path
            d="M2.01 21L23 12L2.01 3L2 10L17 12L2 14L2.01 21Z"
            fill="currentColor"
        />
    </svg>
);

const LoadingSpinner = () => (
    <div className="flex items-center justify-center space-x-2">
        <div className="w-2 h-2 bg-blue-300 rounded-full animate-pulse [animation-delay:-0.3s]"></div>
        <div className="w-2 h-2 bg-blue-300 rounded-full animate-pulse [animation-delay:-0.15s]"></div>
        <div className="w-2 h-2 bg-blue-300 rounded-full animate-pulse"></div>
    </div>
);


// const ConfirmationModal = ({ isOpen, onConfirm, onCancel, modelName }) => {
//     if (!isOpen) return null;

//     return (
//         <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex justify-center items-center">
//             <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md mx-4">
//                 <h2 className="text-xl font-bold text-gray-800 mb-4">Change Model?</h2>
//                 <p className="text-gray-600 mb-6">
//                     Are you sure you want to switch to the{" "}
//                     <span className="font-semibold text-cyan-700">{modelName}</span>{" "}
//                     model? This action will reset the current conversation.
//                 </p>
//                 <div className="flex justify-end space-x-4">
//                     <button
//                         onClick={onCancel}
//                         className="px-4 py-2 rounded-lg text-gray-600 bg-gray-200 hover:bg-gray-300 transition-colors"
//                     >
//                         Cancel
//                     </button>
//                     <button
//                         onClick={onConfirm}
//                         className="px-4 py-2 rounded-lg text-white bg-red-600 hover:bg-red-700 transition-colors"
//                     >
//                         Reset and Change
//                     </button>
//                 </div>
//             </div>
//         </div>
//     );
// };

const initialMessages = [
    {
        role: "assistant",
        content: "Hello! Please select a model and ask me anything.",
    },
];

function Chatbot() {

    const outletContext = useOutletContext()
    useEffect(() => {
        setCurrentModel(outletContext)
    }, [outletContext])

    const [messages, setMessages] = useState(initialMessages);
    const [userInput, setUserInput] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [currentModel, setCurrentModel] = useState(availableModels[0]);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [nextModel, setNextModel] = useState(null);
    const [uploadedFile, setUploadedFile] = useState(null); // Keep track of uploaded file

    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };
    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    // const handleFileUpload = async (e) => {
    //     const file = e.target.files[0];
    //     if (!file || isLoading) return;

    //     setIsLoading(true);
    //     let extractedText = "";

    //     try {
    //         if (file.type === "application/pdf") {
    //             extractedText = await extractTextFromPDF(file);
    //         } else if (
    //             file.type ===
    //             "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    //         ) {
    //             extractedText = await extractTextFromDocx(file);
    //         } else {
    //             throw new Error("Unsupported file type");
    //         }

    //         if (!extractedText.trim()) {
    //             throw new Error("File is empty or unreadable");
    //         }

    //         const userFileMessage = {
    //             role: "user",
    //             content: `Uploaded document: ${file.name}\n\n${extractedText.substring(
    //                 0,
    //                 500
    //             )}... (truncated for display, full content sent to model)`,
    //             file: file.name,
    //         };

    //         const newMessagesForAPI = [
    //             ...messages.slice(1),
    //             { role: "user", content: extractedText },
    //         ];
    //         setMessages((prev) => [...prev, userFileMessage]);

    //         const startTime = performance.now();
    //         const response = await fetch(`${OLLAMA_BASE_URL}/api/chat`, {
    //             method: "POST",
    //             headers: { "Content-Type": "application/json" },
    //             body: JSON.stringify({
    //                 model: currentModel,
    //                 messages: newMessagesForAPI,
    //                 stream: false,
    //             }),
    //         });

    //         const endTime = performance.now();
    //         const duration = ((endTime - startTime) / 1000).toFixed(2);

    //         const data = await response.json();

    //         if (data.message?.content) {
    //             const cleanedContent = data.message.content
    //                 .replace(/<think>[\s\S]*?<\/think>/g, "")
    //                 .trim();
    //             const assistantMessage = {
    //                 role: "assistant",
    //                 content: cleanedContent,
    //                 responseTime: `${duration}s`,
    //             };
    //             setMessages((prev) => [...prev, assistantMessage]);
    //         } else {
    //             throw new Error("No response from model");
    //         }
    //     } catch (error) {
    //         console.error("File processing failed:", error);
    //         setMessages((prev) => [
    //             ...prev,
    //             {
    //                 role: "assistant",
    //                 content: `Error analyzing the document: ${error.message}`,
    //                 responseTime: null,
    //             },
    //         ]);
    //     } finally {
    //         setIsLoading(false);
    //         e.target.value = "";
    //         setUploadedFile(null);
    //     }
    // };

    const handleSendMessage = async () => {
        if ((!userInput.trim() && !uploadedFile) || isLoading) return;

        setIsLoading(true);

        let fileContent = "";
        let displayFileName = null;

        if (uploadedFile) {
            displayFileName = uploadedFile.name;
            try {
                if (uploadedFile.type === "application/pdf") {
                    fileContent = await extractTextFromPDF(uploadedFile);
                } else if (
                    uploadedFile.type ===
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                ) {
                    fileContent = await extractTextFromDocx(uploadedFile);
                } else {
                    throw new Error("Unsupported file type");
                }
            } catch (error) {
                console.error("Error processing attached file:", error);
                setMessages((prev) => [
                    ...prev,
                    {
                        role: "assistant",
                        content: `Failed to process the attached file: ${error.message}`,
                        responseTime: null,
                    },
                ]);
                setIsLoading(false);
                setUploadedFile(null);
                return;
            }
        }

        const newUserMessage = {
            role: "user",
            content: userInput.trim(),
            file: displayFileName,
        };

        const newMessagesForUI = [...messages, newUserMessage];
        setMessages(newMessagesForUI);
        setUserInput("");
        setUploadedFile(null);

        const promptWithFile = fileContent.trim()
            ? `${fileContent.trim()}\n\n${userInput.trim()}`
            : userInput.trim();
        const messagesForAPI = [
            ...newMessagesForUI
                .slice(1)
                .filter((msg) => msg.role !== "user" || msg.file === null),
            { role: "user", content: promptWithFile },
        ];

        const startTime = performance.now();
        try {
            const response = await fetch(`${OLLAMA_BASE_URL}/api/chat`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    model: currentModel,
                    messages: messagesForAPI,
                    stream: false,
                }),
            });

            const endTime = performance.now();
            const duration = ((endTime - startTime) / 1000).toFixed(2);

            setIsLoading(false);
            if (!response.ok)
                throw new Error(`HTTP error! status: ${response.status}`);

            const data = await response.json();
            if (data.message?.content) {
                const cleanedContent = data.message.content
                    .replace(/<think>[\s\S]*?<\/think>/g, "")
                    .trim();
                const assistantMessage = {
                    role: "assistant",
                    content: cleanedContent,
                    responseTime: `${duration}s`,
                };
                setMessages((prev) => [...prev, assistantMessage]);
            } else {
                throw new Error("Invalid response structure from API.");
            }
        } catch (error) {
            console.error("API Call Failed:", error);
            setIsLoading(false);
            setMessages((prev) => [
                ...prev,
                {
                    role: "assistant",
                    content: `Sorry, I encountered an error: ${error.message}`,
                    responseTime: null,
                },
            ]);
        }
    };

    const handleKeyPress = (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    };

    // const handleModelSelect = (model) => {
    //     if (model === currentModel) return;
    //     setNextModel(model);
    //     setIsModalOpen(true);
    // };

    // const handleConfirmChange = () => {
    //     if (nextModel) {
    //         setCurrentModel(nextModel);
    //         setMessages(initialMessages);
    //     }
    //     setIsModalOpen(false);
    //     setNextModel(null);
    // };

    const handleCancelChange = () => {
        setIsModalOpen(false);
        setNextModel(null);
    };

    return (
        <>
            {/* <ConfirmationModal
                isOpen={isModalOpen}
                onConfirm={handleConfirmChange}
                onCancel={handleCancelChange}
                modelName={nextModel}
            /> */}
            <div className="font-sans flex h-screen w-full max-w-[800px]">
                <div className="flex-1 flex flex-col ">
                    <header className=" shadow-sm p-4 text-green-500 text-center border-b ">
                        <h1 className="text-2xl font-bold">Chat Interface</h1>
                        <p className="text-sm text-gray-500">
                            Using model:{" "}
                            <span className="font-semibold text-red-700">{currentModel}</span>
                        </p>
                    </header>

                    <div className="flex-1 p-4 overflow-y-auto  backdrop-blur-sm">
                        <div className="max-w-3xl mx-auto space-y-4">
                            {messages.map((msg, index) => (
                                <div
                                    key={index}
                                    className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"
                                        }`}
                                >
                                    <div
                                        className={`max-w-lg lg:max-w-xl px-4 py-3 rounded-2xl shadow ${msg.role === "user"
                                            ? " text-white rounded-br-none border-green-500 border"
                                            : "border-green-500 border text-white rounded-bl-none"
                                            }`}
                                    >
                                        <div
                                            className={`
                      prose prose-sm max-w-none
                      ${msg.role === "user" ? "prose-invert" : ""}
                      prose-p:mt-0 prose-p:mb-3 prose-li:my-0
                      prose-code:text-pink-400 prose-pre:bg-gray-800 prose-pre:text-white
                    `}
                                        >
                                            {msg.file && (
                                                <div className="text-sm mb-1 text-gray-500 flex items-center gap-2">
                                                    <span className="text-xl ">
                                                        <img
                                                            src="https://www.shareicon.net/data/2016/07/03/636103_file_512x512.png"
                                                            className="w-5"
                                                            alt=""
                                                        />
                                                    </span>{" "}
                                                    {msg.file}
                                                </div>
                                            )}
                                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                                {msg.content}
                                            </ReactMarkdown>
                                        </div>
                                        {msg.role === "assistant" && msg.responseTime && (
                                            <div className="text-right text-xs text-gray-500 mt-2">
                                                response time : {msg.responseTime}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            ))}
                            {isLoading && (
                                <div className="flex justify-start">
                                    <div className="bg-gray-200 text-gray-800 rounded-2xl rounded-bl-none p-3 shadow">
                                        <LoadingSpinner />
                                    </div>
                                </div>
                            )}
                            <div ref={messagesEndRef} />
                        </div>
                    </div>
                    <footer className=" border-t border-green-500 p-4">
                        <div className="max-w-3xl mx-auto flex items-center gap-3">
                            <input
                                type="file"
                                accept=".pdf,.docx"
                                onChange={(e) => setUploadedFile(e.target.files[0])}
                                className="hidden"
                                id="fileInput"
                            />
                            <label
                                htmlFor="fileInput"
                                className="cursor-pointer px-3 py-2 rounded-xl border-green-500 border font-bold text-white hover:bg-gray-300 transition text-sm flex items-center gap-2"
                            >
                                <img
                                    src="https://www.shareicon.net/data/2016/07/03/636103_file_512x512.png"
                                    className="w-5"
                                    alt=""
                                />
                                {uploadedFile ? uploadedFile.name : "Upload"}
                            </label>
                            <textarea
                                value={userInput}
                                onChange={(e) => setUserInput(e.target.value)}
                                onKeyPress={handleKeyPress}
                                placeholder="Type your message..."
                                rows="1"
                                className="flex-1 w-full p-3 text-white border border-green-500 rounded-2xl resize-none focus:ring-2 focus:ring-green-500 focus:outline-none transition"
                                disabled={isLoading}
                            />
                            <button
                                onClick={handleSendMessage}
                                disabled={
                                    isLoading || (!userInput.trim() && !uploadedFile)
                                }
                                className=" p-3 bg-blue-600 rounded-full hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 shadow-lg"
                            >
                                <SendIcon />
                            </button>
                        </div>
                    </footer>
                </div>
            </div>
        </>
    );
}

export default Chatbot;