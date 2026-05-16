import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'SCADA Dashboard',
  description: 'Industrial SCADA Web System',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="es">
      <body className="bg-gray-950 text-gray-100 min-h-screen">
        <nav className="bg-gray-900 border-b border-gray-800 px-6 py-3 flex items-center gap-6">
          <span className="font-bold text-lg text-blue-400">SCADA</span>
          <a href="/" className="text-sm text-gray-300 hover:text-white">Dashboard</a>
          <a href="/devices" className="text-sm text-gray-300 hover:text-white">Dispositivos</a>
          <a href="/templates" className="text-sm text-gray-300 hover:text-white">Templates</a>
          <div className="ml-auto text-xs text-gray-500">
            Desarrollado por{' '}
            <a href="https://mifsut.com" target="_blank" rel="noopener noreferrer"
               className="text-blue-500 hover:text-blue-400 transition-colors">
              mifsut.com
            </a>
          </div>
        </nav>
        <main className="p-6 pb-10">{children}</main>
        <footer className="fixed bottom-0 left-0 right-0 bg-gray-900 border-t border-gray-800 px-6 py-2 flex items-center justify-center">
          <span className="text-xs text-gray-600">
            &copy; {new Date().getFullYear()} Desarrollado por{' '}
            <a href="https://mifsut.com" target="_blank" rel="noopener noreferrer"
               className="text-blue-600 hover:text-blue-500 transition-colors">
              mifsut.com
            </a>
            {' '}— SCADA Web Industrial
          </span>
        </footer>
      </body>
    </html>
  )
}
