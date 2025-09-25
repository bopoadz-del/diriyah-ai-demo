
import React from 'react';
import logo from '../public/masterise-logo.png';

function Sidebar() {
  return (
    <aside style={{ width: '240px', backgroundColor: '#f8f8f8', height: '100vh', padding: '20px', boxShadow: '2px 0 4px rgba(0,0,0,0.1)' }}>
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: '20px' }}>
        <img src={logo} alt="Diriyah Brain Logo" style={{ height: '50px', marginRight: '10px' }} />
        <span style={{ fontSize: '18px', fontWeight: 'bold', color: '#444' }}>Diriyah Brain</span>
      </div>
      {/* Add sidebar links/components here */}
    </aside>
  );
}

export default Sidebar;
