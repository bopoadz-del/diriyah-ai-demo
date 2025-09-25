
import React from 'react';
import logo from '../public/masterise-logo.png';

function Navbar() {
  return (
    <nav style={{ display: 'flex', alignItems: 'center', padding: '10px', backgroundColor: '#fff', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
      <img src={logo} alt="Diriyah Brain Logo" style={{ height: '40px', marginRight: '10px' }} />
      <h1 style={{ fontSize: '20px', color: '#444' }}>Diriyah Brain AI</h1>
    </nav>
  );
}

export default Navbar;
