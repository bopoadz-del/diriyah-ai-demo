import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import ChatWindow from "./components/ChatWindow";
import Analytics from "./components/Analytics";
import Settings from "./components/Settings";
import SplitLayout from "./components/SplitLayout";
import Navbar from "./components/Navbar";
import Sidebar from "./components/Sidebar";
function App() {
  return (
    <Router>
      <div className="app-container">
        <Navbar />
        <div className="content">
          <Sidebar onSelectProject={(id) => console.log("Project selected:", id)} />
          <div className="main-view">
            <Routes>
              <Route path="/" element={<ChatWindow />} />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/split" element={<SplitLayout />} />
            </Routes>
          </div>
        </div>
      </div>
    </Router>
  );
}
export default App;
