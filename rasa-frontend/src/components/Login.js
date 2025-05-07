// src/components/Login.js
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import db from '../db';

function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();

    // Try to fetch the user from the 'users' store
    const user = await db.users.where('username').equals(username).first();

    if (user) {
      // If user exists, check the password
      if (user.password === password) {
        sessionStorage.setItem('currentUser', username);
        navigate('/chat');
      } else {
        alert('Incorrect password. Please try again.');
      }
    } else {
      // If the user does not exist, prompt to register
      if (window.confirm('User not found. Would you like to register?')) {
        // Add new user to the database
        await db.users.add({ username, password });
        // Optionally, create an empty chat history record for the new user
        await db.chatHistory.add({ username, messages: [] });
        sessionStorage.setItem('currentUser', username);
        navigate('/chat');
      }
    }
  };

  return (
    <div className="login-container" style={{ margin: '50px auto', width: '300px' }}>
      <h2>Login / Register</h2>
      <form onSubmit={handleLogin}>
        <div>
          <label>Username:</label>
          <input 
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required 
            style={{ width: '100%', marginBottom: '10px' }}
          />
        </div>
        <div>
          <label>Password:</label>
          <input 
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required 
            style={{ width: '100%', marginBottom: '10px' }}
          />
        </div>
        <button type="submit" style={{ width: '100%' }}>Login / Register</button>
      </form>
    </div>
  );
}

export default Login;
