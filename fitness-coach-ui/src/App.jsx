import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import Home from "./pages/Home";
import Dashboard from "./pages/Dashboard";
import Workout from "./pages/Workout";
import Diet from "./pages/Diet";
import Exercises from "./pages/Exercises";

/**
 * App — root component with React Router setup.
 * All pages share the sticky Navbar.
 */
export default function App() {
  return (
    <Router>
      <div className="min-h-screen bg-dark text-gray-100">
        <Navbar />
        <Routes>
          <Route path="/"          element={<Home />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/workout"   element={<Workout />} />
          <Route path="/diet"      element={<Diet />} />
          <Route path="/exercises" element={<Exercises />} />
        </Routes>
      </div>
    </Router>
  );
}
