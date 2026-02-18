import { Outlet, Link, useLocation } from 'react-router-dom'
import { useState, useEffect } from 'react'
import SearchModal from './SearchModal'
import { SearchIcon } from './icons'

export default function Layout() {
  const location = useLocation()
  const [isSearchOpen, setIsSearchOpen] = useState(false)

  const navLinks = [
    { path: '/', label: 'Dashboard' },
    { path: '/registry', label: 'Feature Registry' },
    { path: '/releases', label: 'Release History' },
    { path: '/glossary', label: 'Glossary' },
  ]

  const isActive = (path: string) => {
    if (path === '/') return location.pathname === '/'
    if (path === '/registry') {
      return location.pathname.startsWith('/registry')
        || location.pathname.startsWith('/features/')
        || location.pathname.startsWith('/options/')
        || location.pathname.startsWith('/settings/')
    }
    return location.pathname.startsWith(path)
  }

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setIsSearchOpen(true)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  return (
    <div className="min-h-screen bg-surface-0">
      {/* Skip to content */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:px-4 focus:py-2 focus:bg-signal-blue focus:text-white focus:rounded-md focus:text-sm focus:font-medium"
      >
        Skip to main content
      </a>

      {/* Header */}
      <header className="sticky top-0 z-40 border-b border-zinc-800/80 bg-surface-0/80 backdrop-blur-xl">
        <div className="max-w-[1400px] mx-auto px-4 sm:px-6">
          <div className="flex items-center justify-between h-12">
            {/* Logo */}
            <Link to="/" className="flex items-center gap-2.5 group">
              <div className="w-6 h-6 rounded bg-signal-green/20 border border-signal-green/30 flex items-center justify-center">
                <span className="text-signal-green font-mono text-xs font-bold">C</span>
              </div>
              <span className="font-mono text-sm font-medium text-zinc-200 group-hover:text-white transition-colors tracking-tight">
                canvas<span className="text-zinc-500">/</span>tracker
              </span>
            </Link>

            {/* Navigation */}
            <nav className="hidden md:flex items-center gap-0.5">
              {navLinks.map((link) => (
                <Link
                  key={link.path}
                  to={link.path}
                  className={`
                    px-3 py-1.5 rounded-md text-[13px] font-medium transition-colors
                    ${isActive(link.path)
                      ? 'bg-zinc-800 text-white'
                      : 'text-zinc-500 hover:text-zinc-300'
                    }
                  `}
                >
                  {link.label}
                </Link>
              ))}
            </nav>

            {/* Search trigger */}
            <button
              onClick={() => setIsSearchOpen(true)}
              className="
                flex items-center gap-2 px-2.5 py-1.5 w-52
                bg-surface-2 border border-zinc-800 rounded-md
                text-[13px] text-zinc-500
                hover:border-zinc-700 hover:text-zinc-400
                transition-colors
              "
            >
              <SearchIcon className="w-3.5 h-3.5" />
              <span className="flex-1 text-left">Search...</span>
              <kbd className="hidden sm:inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-surface-3 border border-zinc-700 rounded text-xs font-mono text-zinc-400">
                <span className="text-xs">⌘</span>K
              </kbd>
            </button>
          </div>
        </div>

        {/* Mobile navigation */}
        <nav className="md:hidden border-t border-zinc-800/50 px-4 py-1.5 flex gap-0.5 overflow-x-auto">
          {navLinks.map((link) => (
            <Link
              key={link.path}
              to={link.path}
              className={`
                px-3 py-1 rounded-md text-[13px] font-medium whitespace-nowrap transition-colors
                ${isActive(link.path)
                  ? 'bg-zinc-800 text-white'
                  : 'text-zinc-500'
                }
              `}
            >
              {link.label}
            </Link>
          ))}
        </nav>
      </header>

      {/* Main content */}
      <main id="main-content" className="max-w-[1400px] mx-auto px-4 sm:px-6 py-6">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="border-t border-zinc-800/50 mt-12">
        <div className="max-w-[1400px] mx-auto px-4 sm:px-6 py-6">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
            <span className="text-xs font-mono text-zinc-500">
              canvas/tracker <span className="text-zinc-500">v2.0</span>
            </span>
            <div className="flex items-center gap-4 text-xs font-mono text-zinc-500">
              <a
                href="https://community.canvaslms.com"
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-zinc-400 transition-colors"
              >
                community
              </a>
              <a
                href="https://community.canvaslms.com/t5/Canvas-Release-Notes/tkb-p/releasenotes"
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-zinc-400 transition-colors"
              >
                release-notes
              </a>
            </div>
          </div>
        </div>
      </footer>

      <SearchModal isOpen={isSearchOpen} onClose={() => setIsSearchOpen(false)} />
    </div>
  )
}
