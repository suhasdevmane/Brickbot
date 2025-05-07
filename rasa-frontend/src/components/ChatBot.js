// src/components/ChatBot.js
import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import Message from './Message';
import { Container, Button, Form } from 'react-bootstrap';
import { BsDownload, BsTrash, BsDashSquare, BsChatDotsFill, BsFullscreen, BsFullscreenExit } from 'react-icons/bs';
import db from '../db';
import '../App.css'; // Ensure CSS is imported

const RASA_ENDPOINT = "http://localhost:5005/webhooks/rest/webhook";

function ChatBot() {
  const [messages, setMessages] = useState([]);
  const [userInput, setUserInput] = useState('');
  const [minimized, setMinimized] = useState(false);
  const [isFullScreen, setIsFullScreen] = useState(false);
  const [isLoading, setIsLoading] = useState(false); // New loading state
  const textAreaRef = useRef(null);
  const messagesEndRef = useRef(null);
  const currentUser = sessionStorage.getItem('currentUser');

  // Load chat history on mount
  useEffect(() => {
    if (currentUser) {
      db.chatHistory.where('username').equals(currentUser).first().then(record => {
        if (record && record.messages && record.messages.length > 0) {
          setMessages(record.messages);
        } else {
          setMessages([{
            sender: 'bot',
            text: 'Welcome to our chat! How can I help you today?',
            timestamp: new Date().toLocaleTimeString(),
          }]);
        }
      });
    }
  }, [currentUser]);

  // Save chat history and auto-scroll
  useEffect(() => {
    if (currentUser) {
      db.chatHistory.where('username').equals(currentUser).first().then(record => {
        if (record) {
          db.chatHistory.update(record.id, { messages });
        } else {
          db.chatHistory.add({ username: currentUser, messages });
        }
      });
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, currentUser]);

  const addMessage = (message) => {
    if (!message.timestamp) {
      message.timestamp = new Date().toLocaleTimeString();
    }
    setMessages(prev => [...prev, message]);
  };

  const sendMessage = async () => {
    if (!userInput.trim()) return;
    const userMessage = {
      sender: 'user',
      text: userInput,
      timestamp: new Date().toLocaleTimeString(),
    };
    addMessage(userMessage);
    setIsLoading(true); // Set loading state to true
    try {
      const response = await axios.post(RASA_ENDPOINT, { sender: 'user', message: userInput });
      const botMessages = response.data.map(msg => ({
        sender: 'bot',
        ...msg,
        timestamp: new Date().toLocaleTimeString(),
      }));
      botMessages.forEach(msg => addMessage(msg));
    } catch (error) {
      console.error("Error communicating with Rasa:", error);
      addMessage({
        sender: 'bot',
        text: "Error communicating with the server.",
        timestamp: new Date().toLocaleTimeString(),
      });
    } finally {
      setIsLoading(false); // Clear loading state
    }
    setUserInput('');
    if (textAreaRef.current) {
      textAreaRef.current.style.height = 'auto';
    }
  };

  const handleTextAreaChange = (e) => {
    setUserInput(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = `${e.target.scrollHeight}px`;
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const downloadChatHistory = () => {
    const element = document.createElement("a");
    const file = new Blob([JSON.stringify(messages, null, 2)], { type: 'application/json' });
    element.href = URL.createObjectURL(file);
    element.download = "chatHistory.json";
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  const clearChatHistory = () => {
    if (currentUser) {
      db.chatHistory.where('username').equals(currentUser).modify({ messages: [] });
    }
    setMessages([]);
  };

  const toggleMinimize = () => {
    setMinimized(prev => !prev);
  };

  // Toggle full-screen mode using the Fullscreen API
  const toggleFullScreen = () => {
    const elem = document.getElementById('chat-container');
    if (!document.fullscreenElement) {
      if (elem.requestFullscreen) {
        elem.requestFullscreen();
      } else if (elem.mozRequestFullScreen) {
        elem.mozRequestFullScreen();
      } else if (elem.webkitRequestFullscreen) {
        elem.webkitRequestFullscreen();
      } else if (elem.msRequestFullscreen) {
        elem.msRequestFullscreen();
      }
      setIsFullScreen(true);
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen();
      }
      setIsFullScreen(false);
    }
  };

  // Define container style dynamically based on full-screen mode
  const containerStyle = isFullScreen
    ? {
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '900vh',
        margin: 0,
        padding: 0,
        zIndex: 10000,
      }
    : {
        position: 'fixed',
        bottom: '20px',
        right: '20px',
        maxWidth: '500px',
        height: '640px',
        padding: 0,
        zIndex: 9999,
      };

  // Use a different className in full-screen mode to avoid default constraints.
  const containerClass = isFullScreen ? "fullscreen-chat-container" : "chat-container";

  // Full chat UI view
  const fullChatUI = (
    <Container id="chat-container" className={containerClass} style={containerStyle}>
      <div className="chat-inner">
        {/* Header */}
        <div className="chat-header">
          <h5 className="mb-0"> 💬 BrickBot</h5>
          <div className="header-buttons">
            <Button variant="light" size="sm" onClick={toggleFullScreen}>
              {isFullScreen ? <BsFullscreenExit /> : <BsFullscreen />}
            </Button>
            <Button variant="light" size="sm" onClick={toggleMinimize}>
              <BsDashSquare />
            </Button>
          </div>
        </div>
        {/* Messages */}
        <div className="chat-messages">
          {messages.map((msg, index) => (
            <Message key={index} message={msg} />
          ))}
          {isLoading && (
            <div className="processing-message text-center my-2">
              <span className="processing-text">Processing... please wait.</span>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
        {/* Input */}
        <div className="chat-input">
          <div className="input-wrapper">
            <Form>
              <Form.Group controlId="chatInput">
                <Form.Control 
                  as="textarea"
                  rows={3}
                  ref={textAreaRef}
                  placeholder="Type your message..."
                  value={userInput}
                  onChange={handleTextAreaChange}
                  onKeyDown={handleKeyDown}
                  style={{ resize: 'none', overflow: 'hidden' }}
                />
              </Form.Group>
            </Form>
          </div>
          <div className="chat-buttons">
            <Button variant="secondary" onClick={downloadChatHistory}>
              <BsDownload size={20} />
            </Button>
            <Button variant="danger" onClick={clearChatHistory}>
              <BsTrash size={20} />
            </Button>
          </div>
        </div>
      </div>
    </Container>
  );

  const minimizedView = (
    <div className="chat-minimized" style={{ position: 'fixed', bottom: '20px', right: '20px', zIndex: 9999 }}>
      <Button variant="primary" onClick={toggleMinimize} style={{ borderRadius: '50%', width: '60px', height: '60px', padding: 0 }}>
        <BsChatDotsFill size={30} />
      </Button>
    </div>
  );

  return (
    <>
      {minimized ? minimizedView : fullChatUI}
    </>
  );
}

export default ChatBot;
