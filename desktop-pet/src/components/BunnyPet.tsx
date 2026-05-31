import { useState, useEffect, useCallback } from 'react'
import NotificationBadge from './NotificationBadge'
import { fetchUnreadCount } from '../middleware/api'
import '../styles/BunnyPet.css'

function BunnyPet() {
    const [unreadCount, setUnreadCount] = useState(0)
    const [mood, setMood] = useState<'idle' | 'excited' | 'sleeping'>('idle')
    const [blinking, setBlinking] = useState(false)
    const [bouncing, setBouncing] = useState(false)
    const [showIntro, setShowIntro] = useState(true)

    useEffect(() => {
        const timer = setTimeout(() => setShowIntro(false), 4500)
        return () => clearTimeout(timer)
    }, [])

    const pollUnread = useCallback(async () => {
        try {
            const count = await fetchUnreadCount()
            setUnreadCount(count)
            if (count > 0) {
                setMood('excited')
                setBouncing(true)
                setTimeout(() => setBouncing(false), 2000)
            } else {
                setMood('idle')
            }
        } catch {
            setMood('idle')
        }
    }, [])

    useEffect(() => {
        pollUnread()
        const interval = setInterval(pollUnread, 5000)
        return () => clearInterval(interval)
    }, [pollUnread])

    useEffect(() => {
        const blinkInterval = setInterval(() => {
            setBlinking(true)
            setTimeout(() => setBlinking(false), 200)
        }, 3000 + Math.random() * 2000)
        return () => clearInterval(blinkInterval)
    }, [])

    useEffect(() => {
        if (!window.electronAPI) return
        const cleanup = window.electronAPI.onPetClicked(() => {
            window.electronAPI?.toggleSummary()
            setBouncing(true)
            setTimeout(() => setBouncing(false), 600)
        })
        return cleanup
    }, [])

    const speechText = showIntro
        ? "Hi! I'm TamaBotchi"
        : mood === 'excited'
        ? `${unreadCount} new!`
        : null

    return (
        <div
            className={`pet-container ${bouncing ? 'pet-container--bounce' : ''}`}
            onMouseDown={() => window.electronAPI?.notifyMouseDown()}
            onMouseUp={() => window.electronAPI?.notifyMouseUp()}
        >
            <NotificationBadge count={unreadCount} />

            {speechText && (
                <div className={`pet-speech-bubble ${showIntro ? 'pet-speech-bubble--intro' : ''}`}>
                    <span>{speechText}</span>
                </div>
            )}

            <svg
                className={`pet-svg ${mood === 'excited' && !showIntro ? 'pet-svg--excited' : ''}`}
                viewBox="0 0 120 148"
                width="120"
                height="148"
                xmlns="http://www.w3.org/2000/svg"
            >
                {/* Avocado outer skin */}
                <path
                    d="M 60 8 C 76 8, 96 28, 98 62 C 99 92, 90 120, 80 132 C 72 140, 48 140, 40 132 C 30 120, 21 92, 22 62 C 24 28, 44 8, 60 8 Z"
                    fill="#2d6a4f"
                    stroke="#1a4a35"
                    strokeWidth="1.5"
                />

                {/* Avocado flesh */}
                <path
                    d="M 60 17 C 73 17, 88 33, 90 63 C 91 89, 84 114, 76 125 C 69 132, 51 132, 44 125 C 36 114, 29 89, 30 63 C 32 33, 47 17, 60 17 Z"
                    fill="#d4f09a"
                    stroke="#b8dc7a"
                    strokeWidth="1"
                />

                {/* Avocado pit */}
                <ellipse cx="60" cy="90" rx="19" ry="23" fill="#7a3b1e" stroke="#5a2b10" strokeWidth="1" />
                <ellipse cx="54" cy="83" rx="5" ry="6" fill="#a0522d" opacity="0.45" />

                {/* Eyes */}
                {blinking ? (
                    <>
                        <line x1="46" y1="53" x2="54" y2="53" stroke="#2d3748" strokeWidth="2.5" strokeLinecap="round" />
                        <line x1="66" y1="53" x2="74" y2="53" stroke="#2d3748" strokeWidth="2.5" strokeLinecap="round" />
                    </>
                ) : (
                    <>
                        <ellipse cx="50" cy="53" rx="5" ry="5.5" fill="#2d3748" />
                        <ellipse cx="70" cy="53" rx="5" ry="5.5" fill="#2d3748" />
                        <circle cx="48" cy="51" r="1.8" fill="#ffffff" />
                        <circle cx="68" cy="51" r="1.8" fill="#ffffff" />
                    </>
                )}

                {/* Mouth */}
                <path d="M 52 64 Q 60 71 68 64" fill="none" stroke="#2d3748" strokeWidth="1.8" strokeLinecap="round" />

                {/* Blush */}
                <circle cx="39" cy="60" r="6" fill="#ffb6c1" opacity="0.3" />
                <circle cx="81" cy="60" r="6" fill="#ffb6c1" opacity="0.3" />
            </svg>

            <div className="pet-shadow" />
        </div>
    )
}

export default BunnyPet
