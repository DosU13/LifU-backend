import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import { App } from './App'
// Tokens first: the older stylesheet still overrides some of them while the
// Part II layouts are being built out, and is deleted in Phase 23.
import './ui/tokens.css'
import './styles.css'

const root = document.getElementById('root')
if (!root) throw new Error('missing #root element')

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
