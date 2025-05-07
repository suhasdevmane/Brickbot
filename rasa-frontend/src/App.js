// src/App.js
import React from 'react';
import { BrowserRouter as Router, Route, Routes, Navigate } from 'react-router-dom';
import ChatBot from './components/ChatBot';
import Login from './components/Login';
import Home from './components/Home';

function App() {
  const currentUser = sessionStorage.getItem('currentUser');

  return (
    <Router>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/chat"
          element={
            currentUser
              ? (
                <>
                  <Home />      {/* background content */}
                  <ChatBot />   {/* floating widget */}
                </>
              )
              : <Navigate to="/login" />
          }
        />
        <Route path="*" element={<Navigate to="/login" />} />
      </Routes>
    </Router>
  );
}

export default App;
