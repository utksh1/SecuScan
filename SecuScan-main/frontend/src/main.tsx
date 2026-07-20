import React from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App'

const el = document.getElementById('root')!
createRoot(el).render(<App />)

