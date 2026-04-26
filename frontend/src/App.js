import { BrowserRouter as Router, Routes, Route } from "react-router-dom";

import Register from "./pages/Register";
import Products from "./pages/Products";
import Dashboard from "./pages/Dashboard";
import Chatbot from "./pages/Chatbot";
import TryOnPage from "./pages/TryOnPage";
import OutfitScheduler from "./pages/OutfitScheduler";

import SkinProgress from "./pages/SkinProgress";
import SavedProducts from "./pages/SavedProducts";
import WeatherBanner from "./pages/WeatherBanner";

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Register />} />
        <Route path="/products" element={<Products />} />
        <Route path="/analysis" element={<Dashboard />} />
        <Route path="/chat" element={<Chatbot />} />
        <Route path="/tryon-lab" element={<TryOnPage />} />
        <Route path="/outfit-scheduler" element={<OutfitScheduler />} />

        {/* NEW ROUTES */}
        <Route path="/skin-progress" element={<SkinProgress />} />
        <Route path="/saved-products" element={<SavedProducts />} />
        <Route path="/weather" element={<WeatherBanner />} />
      </Routes>
    </Router>
  );
}

export default App;