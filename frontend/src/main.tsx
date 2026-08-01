import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import { App } from './App'
// Order matters: styles.css is the Part-I stylesheet and redefines :root with
// the old palette, so tokens.css has to come after it to win. Its component
// rules still style the panels that have not been replaced yet. Both this
// import and that file go away in Phase 23.
import './styles.css'
import './ui/tokens.css'

const root = document.getElementById('root')
if (!root) throw new Error('missing #root element')

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
