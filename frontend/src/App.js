
import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import ChatWindow from './components/ChatWindow';
import Navbar from './components/Navbar';

function App() {
  return (
    <div className="app-container" style={{ display: 'flex', height: '100vh' }}>
      <Sidebar />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <Navbar />
        <ChatWindow />
      </div>
    </div>
  );
}

export default App;
