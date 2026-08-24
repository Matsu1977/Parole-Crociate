import { useEffect } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "sonner";
import Landing from "@/pages/Landing";
import Game from "@/pages/Game";

function App() {
  useEffect(() => {
    document.title = "Cruciverba Insieme";
  }, []);
  return (
    <div className="App">
      <Toaster position="top-center" richColors />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/stanza/:code" element={<Game />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
