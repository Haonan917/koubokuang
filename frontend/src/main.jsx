import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, HashRouter } from 'react-router-dom'
import './i18n' // Initialize i18n before App
import './index.css'
import App from './App.jsx'

const Router = import.meta.env?.VITE_USE_HASH_ROUTER === 'true' ? HashRouter : BrowserRouter

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <Router basename={import.meta.env.BASE_URL}>
      <App />
    </Router>
  </StrictMode>,
)
