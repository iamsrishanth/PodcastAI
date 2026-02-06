import { useState, useEffect, useRef, useCallback } from 'react'
import './App.css'

const API_URL = 'http://localhost:8000'

// Generation steps configuration
const STEPS = [
  { step: 1, name: 'Validating Inputs', description: 'Checking portrait images and API keys', icon: '🔍' },
  { step: 2, name: 'Generating Dialogue', description: 'Creating natural conversation with AI', icon: '💬' },
  { step: 3, name: 'Synthesizing Speech', description: 'Converting text to realistic voice audio', icon: '🎙️' },
  { step: 4, name: 'Creating Background', description: 'Generating scene with AI', icon: '🖼️' },
  { step: 5, name: 'Animating Portraits', description: 'Adding lip sync to portraits', icon: '🎭' },
  { step: 6, name: 'Assembling Video', description: 'Combining all elements', icon: '🎬' },
  { step: 7, name: 'Finalizing', description: 'Encoding final video', icon: '✨' }
]

function App() {
  // Form state
  const [portraitA, setPortraitA] = useState(null)
  const [portraitB, setPortraitB] = useState(null)
  const [scenario, setScenario] = useState('')
  const [speakerAName, setSpeakerAName] = useState('Alex')
  const [speakerBName, setSpeakerBName] = useState('Sam')
  const [voiceA, setVoiceA] = useState('en-US-GuyNeural')
  const [voiceB, setVoiceB] = useState('en-US-JennyNeural')
  
  // Generation state
  const [isGenerating, setIsGenerating] = useState(false)
  const [currentJobId, setCurrentJobId] = useState(null)
  const [progress, setProgress] = useState(null)
  const [completedVideo, setCompletedVideo] = useState(null)
  
  // History state
  const [history, setHistory] = useState([])
  const [selectedHistoryItem, setSelectedHistoryItem] = useState(null)
  
  // Toast state
  const [toast, setToast] = useState(null)
  
  // WebSocket ref
  const wsRef = useRef(null)
  
  // Load history on mount
  useEffect(() => {
    fetchHistory()
  }, [])
  
  // WebSocket connection for progress
  useEffect(() => {
    if (currentJobId && isGenerating) {
      const ws = new WebSocket(`ws://localhost:8000/ws/${currentJobId}`)
      
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data)
        setProgress(data)
        
        if (data.status === 'completed') {
          setIsGenerating(false)
          setCompletedVideo(data.output_path)
          showToast('Video generated successfully!', 'success')
          fetchHistory()
        } else if (data.status === 'failed') {
          setIsGenerating(false)
          showToast(`Generation failed: ${data.error}`, 'error')
        }
      }
      
      ws.onerror = () => {
        showToast('WebSocket connection error', 'error')
      }
      
      wsRef.current = ws
      
      return () => ws.close()
    }
  }, [currentJobId, isGenerating])
  
  const fetchHistory = async () => {
    try {
      const response = await fetch(`${API_URL}/api/history`)
      const data = await response.json()
      setHistory(data)
    } catch (error) {
      console.error('Failed to fetch history:', error)
    }
  }
  
  const showToast = (message, type = 'info') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 5000)
  }
  
  const handleFileSelect = (file, setter) => {
    if (file && file.type.startsWith('image/')) {
      const reader = new FileReader()
      reader.onload = (e) => {
        setter({ file, preview: e.target.result })
      }
      reader.readAsDataURL(file)
    }
  }
  
  const handleGenerate = async () => {
    if (!portraitA || !portraitB || !scenario.trim()) {
      showToast('Please provide both portraits and a scenario', 'error')
      return
    }
    
    setIsGenerating(true)
    setProgress(null)
    setCompletedVideo(null)
    
    const formData = new FormData()
    formData.append('portrait_a', portraitA.file)
    formData.append('portrait_b', portraitB.file)
    formData.append('scenario', scenario)
    formData.append('speaker_a_name', speakerAName)
    formData.append('speaker_b_name', speakerBName)
    formData.append('voice_a', voiceA)
    formData.append('voice_b', voiceB)
    
    try {
      const response = await fetch(`${API_URL}/api/generate`, {
        method: 'POST',
        body: formData
      })
      
      const data = await response.json()
      setCurrentJobId(data.job_id)
      setProgress(data.status)
    } catch (error) {
      setIsGenerating(false)
      showToast(`Failed to start generation: ${error.message}`, 'error')
    }
  }
  
  const handleHistorySelect = (item) => {
    setSelectedHistoryItem(item)
    setCompletedVideo(item.output_path)
  }
  
  const handleDeleteHistory = async (e, videoId) => {
    e.stopPropagation()
    try {
      await fetch(`${API_URL}/api/history/${videoId}`, { method: 'DELETE' })
      fetchHistory()
      if (selectedHistoryItem?.id === videoId) {
        setSelectedHistoryItem(null)
        setCompletedVideo(null)
      }
      showToast('Video deleted', 'success')
    } catch (error) {
      showToast('Failed to delete video', 'error')
    }
  }
  
  return (
    <div className="app">
      {/* Sidebar - History */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="logo">
            <div className="logo-icon">🎙️</div>
            PodcastAI
          </div>
        </div>
        
        <div className="history-section">
          <h3 className="history-title">Generation History</h3>
          
          {history.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">📹</div>
              <p>No videos yet</p>
            </div>
          ) : (
            <div className="history-list">
              {history.map((item) => (
                <div
                  key={item.id}
                  className={`history-item ${selectedHistoryItem?.id === item.id ? 'active' : ''}`}
                  onClick={() => handleHistorySelect(item)}
                >
                  <div className="history-item-header">
                    {item.thumbnail_path ? (
                      <img
                        src={`${API_URL}${item.thumbnail_path}`}
                        alt="Thumbnail"
                        className="history-thumbnail"
                      />
                    ) : (
                      <div className="history-thumbnail" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        🎬
                      </div>
                    )}
                    <div className="history-info">
                      <div className="history-scenario">{item.scenario}</div>
                      <div className="history-meta">
                        {item.speaker_a_name} & {item.speaker_b_name} · {Math.round(item.duration)}s
                      </div>
                    </div>
                    <button
                      className="btn btn-icon btn-secondary"
                      onClick={(e) => handleDeleteHistory(e, item.id)}
                      title="Delete"
                    >
                      🗑️
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </aside>
      
      {/* Main Content */}
      <main className="main-content">
        <header className="main-header">
          <h1>Create Conversation Video</h1>
          <p>Upload two portraits and describe the scenario to generate an AI-powered conversation</p>
        </header>
        
        <div className="content-area">
          {/* Generation Progress */}
          {isGenerating && progress && (
            <section className="progress-section">
              <div className="progress-header">
                <h2 className="progress-title">Generating Your Video</h2>
                <div className="progress-percent">{Math.round(progress.progress_percent)}%</div>
              </div>
              
              <div className="progress-bar-container">
                <div 
                  className="progress-bar" 
                  style={{ width: `${progress.progress_percent}%` }}
                />
              </div>
              
              <div className="steps-list">
                {STEPS.map((step) => {
                  const isCompleted = step.step < progress.current_step
                  const isActive = step.step === progress.current_step
                  
                  return (
                    <div
                      key={step.step}
                      className={`step-item ${isCompleted ? 'completed' : ''} ${isActive ? 'active' : ''}`}
                    >
                      <div className="step-number">
                        {isCompleted ? '✓' : isActive ? <div className="loading-spinner" /> : step.step}
                      </div>
                      <div className="step-info">
                        <div className="step-name">{step.icon} {step.name}</div>
                        <div className="step-description">{step.description}</div>
                      </div>
                      {isCompleted && <span className="step-status-icon">✅</span>}
                      {isActive && <span className="step-status-icon">⏳</span>}
                    </div>
                  )
                })}
              </div>
            </section>
          )}
          
          {/* Completed Video */}
          {completedVideo && !isGenerating && (
            <section className="video-preview">
              <h2 className="video-preview-title">
                {selectedHistoryItem ? 'Selected Video' : '🎉 Your Video is Ready!'}
              </h2>
              <video
                className="video-player"
                src={`${API_URL}${completedVideo}`}
                controls
                autoPlay={!selectedHistoryItem}
              />
              <div className="video-actions">
                <a
                  href={`${API_URL}${completedVideo}`}
                  download
                  className="btn btn-primary"
                >
                  📥 Download Video
                </a>
                <button
                  className="btn btn-secondary"
                  onClick={() => {
                    setCompletedVideo(null)
                    setSelectedHistoryItem(null)
                  }}
                >
                  ✨ Create New
                </button>
              </div>
            </section>
          )}
          
          {/* Input Form */}
          {!isGenerating && (
            <section className="form-section">
              <h2 className="form-section-title">
                <span className="icon">📸</span>
                Upload Portraits
              </h2>
              
              <div className="form-row">
                <div className="form-group">
                  <label>Portrait A ({speakerAName})</label>
                  <UploadZone
                    file={portraitA}
                    onFileSelect={(f) => handleFileSelect(f, setPortraitA)}
                    accept="image/*"
                  />
                </div>
                <div className="form-group">
                  <label>Portrait B ({speakerBName})</label>
                  <UploadZone
                    file={portraitB}
                    onFileSelect={(f) => handleFileSelect(f, setPortraitB)}
                    accept="image/*"
                  />
                </div>
              </div>
              
              <h2 className="form-section-title" style={{ marginTop: '32px' }}>
                <span className="icon">💬</span>
                Conversation Details
              </h2>
              
              <div className="form-row">
                <div className="form-group">
                  <label>Speaker A Name</label>
                  <input
                    type="text"
                    value={speakerAName}
                    onChange={(e) => setSpeakerAName(e.target.value)}
                    placeholder="Enter name..."
                  />
                </div>
                <div className="form-group">
                  <label>Speaker B Name</label>
                  <input
                    type="text"
                    value={speakerBName}
                    onChange={(e) => setSpeakerBName(e.target.value)}
                    placeholder="Enter name..."
                  />
                </div>
              </div>
              
              <div className="form-row">
                <div className="form-group">
                  <label>Voice A</label>
                  <select value={voiceA} onChange={(e) => setVoiceA(e.target.value)}>
                    <option value="en-US-GuyNeural">Guy (Male, US)</option>
                    <option value="en-US-ChristopherNeural">Christopher (Male, US)</option>
                    <option value="en-GB-RyanNeural">Ryan (Male, UK)</option>
                    <option value="en-US-JennyNeural">Jenny (Female, US)</option>
                    <option value="en-US-AriaNeural">Aria (Female, US)</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Voice B</label>
                  <select value={voiceB} onChange={(e) => setVoiceB(e.target.value)}>
                    <option value="en-US-JennyNeural">Jenny (Female, US)</option>
                    <option value="en-US-AriaNeural">Aria (Female, US)</option>
                    <option value="en-GB-SoniaNeural">Sonia (Female, UK)</option>
                    <option value="en-US-GuyNeural">Guy (Male, US)</option>
                    <option value="en-US-ChristopherNeural">Christopher (Male, US)</option>
                  </select>
                </div>
              </div>
              
              <div className="form-group full-width">
                <label>Conversation Scenario</label>
                <textarea
                  value={scenario}
                  onChange={(e) => setScenario(e.target.value)}
                  placeholder="Describe what the conversation should be about... e.g., 'Two tech entrepreneurs discussing the future of AI and its impact on society'"
                />
              </div>
              
              <button
                className="btn btn-primary"
                onClick={handleGenerate}
                disabled={!portraitA || !portraitB || !scenario.trim()}
                style={{ marginTop: '24px', width: '100%' }}
              >
                🎬 Generate Conversation Video
              </button>
            </section>
          )}
        </div>
      </main>
      
      {/* Toast Notification */}
      {toast && (
        <div className={`toast ${toast.type}`}>
          {toast.type === 'success' ? '✅' : '❌'} {toast.message}
        </div>
      )}
    </div>
  )
}

// Upload Zone Component
function UploadZone({ file, onFileSelect, accept }) {
  const [isDragOver, setIsDragOver] = useState(false)
  const inputRef = useRef(null)
  
  const handleDrop = useCallback((e) => {
    e.preventDefault()
    setIsDragOver(false)
    const droppedFile = e.dataTransfer.files[0]
    if (droppedFile) onFileSelect(droppedFile)
  }, [onFileSelect])
  
  const handleDragOver = useCallback((e) => {
    e.preventDefault()
    setIsDragOver(true)
  }, [])
  
  const handleDragLeave = useCallback(() => {
    setIsDragOver(false)
  }, [])
  
  return (
    <div
      className={`upload-zone ${isDragOver ? 'drag-over' : ''} ${file ? 'has-file' : ''}`}
      onClick={() => inputRef.current?.click()}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        onChange={(e) => onFileSelect(e.target.files[0])}
        style={{ display: 'none' }}
      />
      
      {file ? (
        <img src={file.preview} alt="Preview" className="upload-preview" />
      ) : (
        <>
          <span className="upload-icon">📷</span>
          <p className="upload-text">Drag & drop or click to upload</p>
          <p className="upload-hint">Supports: JPG, PNG, WebP</p>
        </>
      )}
    </div>
  )
}

export default App
