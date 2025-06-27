import { useQuery } from "@tanstack/react-query";
import logo from "../assets/cerberus-logo.png";
import { getOllamaModelsAPI } from "../api";
import { useEffect } from "react";
import { NavLink } from "react-router-dom";



export default function Sidebar({ setSelectedModel }) {
    const { data: models, isSuccess } = useQuery({
        queryKey: ['models'],
        queryFn: getOllamaModelsAPI,
        staleTime: Infinity
    })
    // console.log(models, 'models')

    useEffect(() => {
        if (isSuccess && models) {
            setSelectedModel(models[0].name)
        }
    }, [isSuccess, models])




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
                        powered by: Ollama
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
                <span className="text-green-800 font-bold text-xl  drop-shadow-green-600 drop-shadow-md border-green-500 hover:border p-2">
                    Coming Soon...
                </span>
                <span className="text-green-800 font-bold text-xl  drop-shadow-green-600 drop-shadow-md border-green-500 hover:border p-2">
                    Coming Soon...
                </span>
            </div>

            {/* footer */}
            <div className="text-green-800 border-dashed flex flex-col border-green-500 ">
                <p className="text-xs text-red-800  drop-shadow-red-600 drop-shadow-md">
                    current model
                </p>
                <select className="p-2 font-bold border-green-500 border" onChange={(e) => {
                    setSelectedModel(e.target.value)
                }}>

                    {models?.map(item => (<option key={item.name} value={item.name}  >{item.name}</option>))}

                </select>
            </div>
        </section>
    );
}
