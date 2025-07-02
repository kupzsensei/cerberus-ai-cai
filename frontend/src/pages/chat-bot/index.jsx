import React, { useState, useRef, useEffect } from "react";
import { useOutletContext } from "react-router-dom";
import MarkdownRenderer from "../../components/MarkdownRenderer";
import { OLLAMA_BASE_URL } from "../../api";

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

const initialMessages = [
    {
        role: "assistant",
        content: "Hello! A new model has been selected. The conversation has been reset.",
    },
];

export default function Chatbot() {
    const { selectedModel, setSelectedModel } = useOutletContext();
    const [messages, setMessages] = useState(initialMessages);
    const [userInput, setUserInput] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [uploadedFile, setUploadedFile] = useState(null);

    const messagesEndRef = useRef(null);
    const isInitialMount = useRef(true); // Ref to track initial mount

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    // This useEffect hook now correctly resets the chat when the model changes.
    useEffect(() => {
        // Skip the reset on the very first render
        if (isInitialMount.current) {
            isInitialMount.current = false;
            return;
        }
        
        if (selectedModel) {
            setMessages(initialMessages);
        }
    }, [selectedModel]); // Only depends on selectedModel

    const handleSendMessage = async () => {
        if ((!userInput.trim() && !uploadedFile) || isLoading) return;

        setIsLoading(true);

        let fileContent = "";
        let displayFileName = null;

        if (uploadedFile) {
            displayFileName = uploadedFile.name;
            try {
                if (uploadedFile.type === "application/pdf") {
                    // This requires a function `extractTextFromPDF` which is assumed to exist
                    // fileContent = await extractTextFromPDF(uploadedFile); 
                } else if (
                    uploadedFile.type ===
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                ) {
                    // This requires a function `extractTextFromDocx` which is assumed to exist
                    // fileContent = await extractTextFromDocx(uploadedFile);
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
                    model: selectedModel,
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
                const assistantMessage = {
                    role: "assistant",
                    content: data.message.content,
                    responseTime: `${duration}s`,
                    modelUsed: selectedModel,
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

    return (
        <>
            <div className="font-sans flex h-screen w-full max-w-[800px]">
                <div className="flex-1 flex flex-col ">
                    <header className=" shadow-sm p-4 text-green-500 text-center border-b ">
                        <h1 className="text-2xl font-bold">Chat Interface</h1>
                        <p className="text-sm text-gray-500">
                            Using model:{" "}
                            <span className="font-semibold text-red-700">{selectedModel}</span>
                        </p>
                    </header>

                    <div className="flex-1 p-4 overflow-y-auto  backdrop-blur-sm">
                        <div className="max-w-3xl mx-auto space-y-4">
                            {messages.map((msg, index) => (
                                <div
                                    key={index}
                                    className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}
                                        `}
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
                                            <MarkdownRenderer content={msg.content} />
                                        </div>
                                        {msg.role === "assistant" && msg.responseTime && (
                                            <div className="text-right text-xs text-gray-500 mt-2">
                                                <span>model: {msg.modelUsed}</span> | <span>response time: {msg.responseTime}</span>
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
