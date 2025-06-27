import { Outlet } from "react-router-dom";
import Sidebar from "./components/sidebar";
import { useState } from "react";

function App() {
  const [selectedModel , setSelectedModel] = useState('gemma3')

  console.log(  'selected models : ', selectedModel)
  return (
    <main className="w-screen h-screen flex bg-black">
      <Sidebar setSelectedModel={setSelectedModel} />
      <section className="flex-1 flex flex-col items-center min-w-0 overflow-auto p-5">
        <Outlet context={selectedModel} />
      </section>
    </main>
  );
}

export default App;
