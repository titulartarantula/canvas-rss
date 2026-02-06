import { Outlet, Link, useLocation } from 'react-router-dom'
import { useState, useEffect } from 'react'
import SearchModal from './SearchModal'
import { SearchIcon, ArchiveIcon } from './icons'

export default function Layout() {
  const location = useLocation()
  const [isSearchOpen, setIsSearchOpen] = useState(false)

  const navLinks = [
    { path: '/', label: 'Dashboard' },
    { path: '/features', label: 'Features' },
    { path: '/options', label: 'Options' },
    { path: '/releases', label: 'Archive' },
  ]

  const isActive = (path: string) => {
    if (path === '/') return location.pathname === '/'
    return location.pathname.startsWith(path)
  }

  // Global keyboard shortcut for search
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Cmd/Ctrl + K to open search
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setIsSearchOpen(true)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  return (
    <div className="min-h-screen bg-ink-50">
      {/* Header */}
      <header className="bg-white border-b border-ink-200 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <Link to="/" className="flex items-center gap-2.5 group">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-accent-primary to-accent-secondary flex items-center justify-center shadow-sm">
                <span className="text-white font-display font-bold text-sm">CF</span>
              </div>
              <span className="font-display text-lg font-semibold text-ink-900 group-hover:text-accent-primary transition-colors">
                Canvas Feature Tracker
              </span>
            </Link>

            {/* Navigation */}
            <nav className="hidden md:flex items-center gap-1">
              {navLinks.map((link) => (
                <Link
                  key={link.path}
                  to={link.path}
                  className={`
                    px-3 py-2 rounded-lg text-sm font-medium transition-all
                    ${isActive(link.path)
                      ? 'bg-ink-100 text-ink-900'
                      : 'text-ink-600 hover:text-ink-900 hover:bg-ink-50'
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
                flex items-center gap-3 px-3 py-2 w-64
                bg-ink-50 border border-ink-200 rounded-lg
                text-sm text-ink-500
                hover:bg-ink-100 hover:border-ink-300
                transition-colors
              "
            >
              <SearchIcon className="w-4 h-4" />
              <span className="flex-1 text-left">Search...</span>
              <kbd className="hidden sm:inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-white border border-ink-200 rounded text-[10px] font-mono text-ink-500">
                <span className="text-xs">⌘</span>K
              </kbd>
            </button>
          </div>
        </div>

        {/* Mobile navigation */}
        <nav className="md:hidden border-t border-ink-100 px-4 py-2 flex gap-1 overflow-x-auto">
          {navLinks.map((link) => (
            <Link
              key={link.path}
              to={link.path}
              className={`
                px-3 py-1.5 rounded-lg text-sm font-medium whitespace-nowrap
                ${isActive(link.path)
                  ? 'bg-ink-100 text-ink-900'
                  : 'text-ink-600'
                }
              `}
            >
              {link.label}
            </Link>
          ))}
        </nav>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="border-t border-ink-200 bg-white mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2 text-sm text-ink-500">
              <ArchiveIcon className="w-4 h-4" />
              <span>Canvas Feature Tracker</span>
            </div>
            <div className="flex items-center gap-6 text-sm text-ink-500">
              <a
                href="https://community.canvaslms.com"
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-ink-700 transition-colors"
              >
                Canvas Community
              </a>
              <a
                href="https://community.canvaslms.com/t5/Canvas-Release-Notes/tkb-p/releasenotes"
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-ink-700 transition-colors"
              >
                Release Notes
              </a>
            </div>
          </div>
        </div>
      </footer>

      {/* Search Modal */}
      <SearchModal isOpen={isSearchOpen} onClose={() => setIsSearchOpen(false)} />
    </div>
  )
}
