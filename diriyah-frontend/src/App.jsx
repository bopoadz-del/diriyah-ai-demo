import { useState, useEffect, useRef } from 'react'
import { Button } from '@/components/ui/button.jsx'
import { Card, CardContent } from '@/components/ui/card.jsx'
import { Input } from '@/components/ui/input.jsx'
import { Badge } from '@/components/ui/badge.jsx'
import { ScrollArea } from '@/components/ui/scroll-area.jsx'
import { Separator } from '@/components/ui/separator.jsx'
import { 
  Plus, 
  Download, 
  Send, 
  Mic, 
  AlertTriangle, 
  CheckCircle, 
  FileText,
  Building,
  Settings,
  LogOut,
  User
} from 'lucide-react'
import diriyahLogo from './assets/diriyah-logo.jpg'
import './App.css'

const API_BASE_URL = 'http://localhost:8080'

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [user, setUser] = useState(null)
  const [loginEmail, setLoginEmail] = useState('')
  const [loginPassword, setLoginPassword] = useState('')
  const [demoUsers, setDemoUsers] = useState([])
  const [currentProject, setCurrentProject] = useState('Heritage Resort')
  const [projects, setProjects] = useState([
    { id: 1, name: 'Heritage Resort' },
    { id: 2, name: 'Boulevard Development' },
    { id: 3, name: 'Infrastructure Package MC0A' },
    { id: 4, name: 'Cultural District' }
  ])
  const [messages, setMessages] = useState([])
  const [inputMessage, setInputMessage] = useState('')
  const [isListening, setIsListening] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    // Check for existing token on app load
    const token = localStorage.getItem('diriyah_token')
    if (token) {
      verifyToken(token)
    }
    
    // Load demo users for testing
    loadDemoUsers()
  }, [])

  const loadDemoUsers = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/demo-users`)
      const data = await response.json()
      setDemoUsers(data.demo_users || [])
    } catch (error) {
      console.error('Failed to load demo users:', error)
    }
  }

  const verifyToken = async (token) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/verify`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      
      if (response.ok) {
        const data = await response.json()
        setUser(data.user)
        setIsAuthenticated(true)
        initializeChat()
      } else {
        localStorage.removeItem('diriyah_token')
      }
    } catch (error) {
      console.error('Token verification failed:', error)
      localStorage.removeItem('diriyah_token')
    }
  }

  const login = async (email, password) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ email, password })
      })
      
      const data = await response.json()
      
      if (response.ok) {
        localStorage.setItem('diriyah_token', data.token)
        setUser(data.user)
        setIsAuthenticated(true)
        initializeChat()
      } else {
        alert(data.error || 'Login failed')
      }
    } catch (error) {
      console.error('Login failed:', error)
      alert('Login failed. Please try again.')
    }
  }

  const logout = () => {
    localStorage.removeItem('diriyah_token')
    setUser(null)
    setIsAuthenticated(false)
    setMessages([])
  }

  const initializeChat = () => {
    setMessages([
      {
        id: 1,
        type: 'system',
        content: '✅ Connected to project Google Drive. Ask in English or Arabic.',
        timestamp: new Date()
      }
    ])
  }

  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return

    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: inputMessage,
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInputMessage('')
    setIsLoading(true)

    try {
      const token = localStorage.getItem('diriyah_token')
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          message: inputMessage,
          project: currentProject
        })
      })

      const data = await response.json()

      if (response.ok) {
        const aiResponse = {
          id: Date.now() + 1,
          type: 'ai',
          content: data.response,
          timestamp: new Date(),
          citations: data.citations || []
        }
        setMessages(prev => [...prev, aiResponse])

        // Sometimes add alerts for demo
        if (Math.random() > 0.7) {
          setTimeout(() => {
            const alert = {
              id: Date.now() + 2,
              type: 'alert',
              content: '⚠️ Delay risk detected in Package MC0A asphalt works - 3 days behind schedule',
              timestamp: new Date(),
              severity: 'warning'
            }
            setMessages(prev => [...prev, alert])
          }, 1000)
        }
      } else {
        const errorMessage = {
          id: Date.now() + 1,
          type: 'alert',
          content: `❌ ${data.error || 'Failed to get response'}`,
          timestamp: new Date(),
          severity: 'error'
        }
        setMessages(prev => [...prev, errorMessage])
      }
    } catch (error) {
      console.error('Chat error:', error)
      const errorMessage = {
        id: Date.now() + 1,
        type: 'alert',
        content: '❌ Connection error. Please try again.',
        timestamp: new Date(),
        severity: 'error'
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const startVoiceInput = () => {
    if ('webkitSpeechRecognition' in window) {
      const recognition = new window.webkitSpeechRecognition()
      recognition.lang = 'ar-SA'
      recognition.interimResults = false
      recognition.maxAlternatives = 1

      recognition.onstart = () => setIsListening(true)
      recognition.onend = () => setIsListening(false)
      
      recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript
        setInputMessage(transcript)
      }

      recognition.start()
    }
  }

  const exportToPDF = () => {
    const chatContent = messages.map(msg => 
      `[${msg.timestamp.toLocaleString()}] ${msg.type.toUpperCase()}: ${msg.content}`
    ).join('\n\n')
    
    const blob = new Blob([chatContent], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `diriyah-chat-${currentProject}-${new Date().toISOString().split('T')[0]}.txt`
    a.click()
  }

  const newChat = () => {
    initializeChat()
  }

  const getMessageBubbleClass = (type) => {
    switch (type) {
      case 'user':
        return 'ml-auto bg-blue-500 text-white max-w-[80%]'
      case 'ai':
        return 'mr-auto bg-amber-50 border border-amber-200 text-amber-900 max-w-[85%]'
      case 'alert':
        return 'mx-auto bg-red-50 border border-red-200 text-red-800 max-w-[90%]'
      case 'system':
        return 'mx-auto bg-green-50 border border-green-200 text-green-800 max-w-[90%]'
      default:
        return 'mr-auto bg-gray-100 max-w-[80%]'
    }
  }

  // Login Screen
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-amber-50 to-orange-100 flex items-center justify-center p-4">
        <Card className="w-full max-w-md bg-white shadow-xl">
          <CardContent className="p-8">
            <div className="text-center mb-8">
              <img 
                src={diriyahLogo} 
                alt="Diriyah Company" 
                className="h-20 w-20 rounded-full object-cover border-2 border-amber-400 mx-auto mb-4"
              />
              <h1 className="text-2xl font-bold text-amber-900">Diriyah Brain AI</h1>
              <p className="text-sm text-amber-700">شركة الدرعية | Diriyah Company</p>
            </div>

            <div className="space-y-4">
              <Input
                type="email"
                placeholder="Email"
                value={loginEmail}
                onChange={(e) => setLoginEmail(e.target.value)}
                className="border-amber-300 focus:border-amber-500"
              />
              <Input
                type="password"
                placeholder="Password"
                value={loginPassword}
                onChange={(e) => setLoginPassword(e.target.value)}
                className="border-amber-300 focus:border-amber-500"
                onKeyPress={(e) => e.key === 'Enter' && login(loginEmail, loginPassword)}
              />
              <Button
                onClick={() => login(loginEmail, loginPassword)}
                className="w-full bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600"
              >
                Login
              </Button>
            </div>

            {demoUsers.length > 0 && (
              <div className="mt-8">
                <Separator className="my-4" />
                <h3 className="text-sm font-semibold text-amber-900 mb-3">Demo Users:</h3>
                <div className="space-y-2">
                  {demoUsers.map((demoUser, idx) => (
                    <Button
                      key={idx}
                      variant="outline"
                      size="sm"
                      className="w-full justify-start text-left h-auto p-3 border-amber-200 hover:bg-amber-50"
                      onClick={() => {
                        setLoginEmail(demoUser.email)
                        setLoginPassword('demo123')
                      }}
                    >
                      <div className="text-left">
                        <div className="font-medium text-xs">{demoUser.name}</div>
                        <div className="text-xs text-amber-600">{demoUser.role_description}</div>
                        <div className="text-xs text-gray-500">{demoUser.email}</div>
                      </div>
                    </Button>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    )
  }

  // Main Chat Interface
  return (
    <div className="h-screen flex flex-col bg-gradient-to-br from-amber-50 to-orange-100">
      {/* Header */}
      <header className="bg-gradient-to-r from-amber-100 to-orange-200 border-b border-amber-300 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <img 
              src={diriyahLogo} 
              alt="Diriyah Company" 
              className="h-12 w-12 rounded-full object-cover border-2 border-amber-400"
            />
            <div>
              <h1 className="text-2xl font-bold text-amber-900">Diriyah Brain AI</h1>
              <p className="text-sm text-amber-700">شركة الدرعية | Diriyah Company</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-right">
              <div className="text-sm font-medium text-amber-900">{user?.name}</div>
              <div className="text-xs text-amber-700">{user?.role_description}</div>
            </div>
            <Badge variant="outline" className="bg-white/50">
              <User className="h-3 w-3 mr-1" />
              {user?.role?.replace('_', ' ').toUpperCase()}
            </Badge>
            <Button variant="ghost" size="sm" onClick={logout}>
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <aside className="w-80 bg-amber-50 border-r border-amber-200 flex flex-col">
          {/* Chat Actions */}
          <div className="p-4 border-b border-amber-200">
            <div className="space-y-3">
              <Button 
                onClick={newChat}
                className="w-full justify-start bg-white hover:bg-amber-100 text-amber-900 border border-amber-300"
                variant="outline"
              >
                <Plus className="h-4 w-4 mr-2" />
                New Chat
              </Button>
              <Button 
                onClick={exportToPDF}
                className="w-full justify-start bg-white hover:bg-amber-100 text-amber-900 border border-amber-300"
                variant="outline"
              >
                <Download className="h-4 w-4 mr-2" />
                Export PDF
              </Button>
            </div>
          </div>

          {/* Projects List */}
          <div className="flex-1 p-4">
            <h3 className="text-sm font-semibold text-amber-900 mb-3 flex items-center gap-2">
              <Building className="h-4 w-4" />
              Projects
            </h3>
            <div className="space-y-2">
              {projects.map(project => {
                // Check if user has access to this project
                const hasAccess = user?.projects?.includes('all') || 
                                user?.projects?.includes(project.name.toLowerCase().replace(' ', '_'))
                
                if (!hasAccess) return null

                return (
                  <Button
                    key={project.id}
                    variant={currentProject === project.name ? "default" : "ghost"}
                    className={`w-full justify-start text-left h-auto p-3 ${
                      currentProject === project.name 
                        ? 'bg-amber-200 text-amber-900 hover:bg-amber-300' 
                        : 'text-amber-800 hover:bg-amber-100'
                    }`}
                    onClick={() => setCurrentProject(project.name)}
                  >
                    <div className="text-sm font-medium truncate">
                      {project.name}
                    </div>
                  </Button>
                )
              })}
            </div>
          </div>

          {/* User Info */}
          <div className="p-4 border-t border-amber-200">
            <div className="text-xs text-amber-700 mb-2">Permissions:</div>
            <div className="flex flex-wrap gap-1">
              {user?.permissions?.data_access?.map((access, idx) => (
                <Badge key={idx} variant="outline" className="text-xs bg-white/50">
                  {access}
                </Badge>
              ))}
            </div>
          </div>
        </aside>

        {/* Main Chat Area */}
        <main className="flex-1 flex flex-col">
          {/* Project Header */}
          <div className="bg-white border-b border-amber-200 px-6 py-3">
            <h2 className="text-lg font-semibold text-amber-900">
              {currentProject}
            </h2>
            <p className="text-sm text-amber-700">
              Connected to Google Drive • Real-time data • Role: {user?.role?.replace('_', ' ')}
            </p>
          </div>

          {/* Messages Area */}
          <ScrollArea className="flex-1 p-6">
            <div className="space-y-4 max-w-4xl mx-auto">
              {messages.map((message) => (
                <div key={message.id} className="flex">
                  <Card className={`${getMessageBubbleClass(message.type)} shadow-sm`}>
                    <CardContent className="p-4">
                      {message.type === 'alert' && (
                        <div className="flex items-start gap-2 mb-2">
                          <AlertTriangle className="h-4 w-4 text-red-500 mt-0.5 flex-shrink-0" />
                        </div>
                      )}
                      {message.type === 'system' && (
                        <div className="flex items-start gap-2 mb-2">
                          <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                        </div>
                      )}
                      <div className="text-sm leading-relaxed whitespace-pre-wrap">
                        {message.content}
                      </div>
                      {message.citations && message.citations.length > 0 && (
                        <div className="mt-3 pt-2 border-t border-amber-200">
                          <div className="text-xs text-amber-600 mb-1">Sources:</div>
                          <div className="flex flex-wrap gap-1">
                            {message.citations.map((citation, idx) => (
                              <Badge key={idx} variant="outline" className="text-xs bg-white/50">
                                <FileText className="h-3 w-3 mr-1" />
                                {citation}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      )}
                      <div className="text-xs text-amber-600 mt-2 opacity-70">
                        {message.timestamp.toLocaleTimeString()}
                      </div>
                    </CardContent>
                  </Card>
                </div>
              ))}
              {isLoading && (
                <div className="flex">
                  <Card className="mr-auto bg-amber-50 border border-amber-200 text-amber-900 max-w-[85%] shadow-sm">
                    <CardContent className="p-4">
                      <div className="text-sm">AI is thinking...</div>
                    </CardContent>
                  </Card>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          </ScrollArea>

          {/* Input Area */}
          <div className="bg-white border-t border-amber-200 p-4">
            <div className="max-w-4xl mx-auto">
              <div className="flex gap-3 items-end">
                <div className="flex-1 relative">
                  <Input
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    placeholder="Type in English or Arabic... اكتب باللغة العربية أو الإنجليزية"
                    className="pr-12 py-3 text-base border-amber-300 focus:border-amber-500 focus:ring-amber-500"
                    onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                    disabled={isLoading}
                    dir="auto"
                  />
                  <Button
                    size="sm"
                    variant="ghost"
                    className={`absolute right-2 top-1/2 -translate-y-1/2 h-8 w-8 p-0 ${
                      isListening ? 'text-red-500 animate-pulse' : 'text-amber-600 hover:text-amber-800'
                    }`}
                    onClick={startVoiceInput}
                    disabled={isLoading}
                  >
                    <Mic className="h-4 w-4" />
                  </Button>
                </div>
                <Button
                  onClick={sendMessage}
                  disabled={!inputMessage.trim() || isLoading}
                  className="bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white px-6 py-3"
                >
                  <Send className="h-4 w-4" />
                </Button>
              </div>
              <div className="text-xs text-amber-600 mt-2 text-center">
                AI responses are filtered based on your role permissions ({user?.role?.replace('_', ' ')})
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}

export default App

