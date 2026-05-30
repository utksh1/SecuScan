import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

export type NotificationType = 'success' | 'error' | 'info' | 'warning'

export interface Notification {
    id: string
    title: string
    message: string
    type: NotificationType
    read: boolean
    timestamp: Date
}

interface NotificationContextType {
    notifications: Notification[]
    unreadCount: number
    addNotification: (title: string, message: string, type?: NotificationType) => void
    markAsRead: (id: string) => void
    markAllAsRead: () => void
    removeNotification: (id: string) => void
    clearAll: () => void
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined)

export const useNotifications = () => {
    const context = useContext(NotificationContext)
    if (!context) throw new Error('useNotifications must be used within NotificationProvider')
    return context
}

export const NotificationProvider = ({ children }: { children: ReactNode }) => {
    const [notifications, setNotifications] = useState<Notification[]>([])

    const addNotification = useCallback((title: string, message: string, type: NotificationType = 'info') => {
        const id = Math.random().toString(36).substring(2, 9)
        const notification: Notification = { id, title, message, type, read: false, timestamp: new Date() }
        setNotifications((prev) => [notification, ...prev].slice(0, 50))

        // Browser notification
        if (Notification.permission === 'granted') {
            new Notification(title, { body: message, icon: '/favicon.ico' })
        }
    }, [])

    const markAsRead = useCallback((id: string) => {
        setNotifications((prev) => prev.map((n) => n.id === id ? { ...n, read: true } : n))
    }, [])

    const markAllAsRead = useCallback(() => {
        setNotifications((prev) => prev.map((n) => ({ ...n, read: true })))
    }, [])

    const removeNotification = useCallback((id: string) => {
        setNotifications((prev) => prev.filter((n) => n.id !== id))
    }, [])

    const clearAll = useCallback(() => setNotifications([]), [])

    const unreadCount = notifications.filter((n) => !n.read).length

    return (
        <NotificationContext.Provider value={{ notifications, unreadCount, addNotification, markAsRead, markAllAsRead, removeNotification, clearAll }}>
            {children}
        </NotificationContext.Provider>
    )
}

function timeAgo(date: Date): string {
    const seconds = Math.floor((new Date().getTime() - date.getTime()) / 1000)
    if (seconds < 60) return 'just now'
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`
    return `${Math.floor(seconds / 86400)}d ago`
}

export function NotificationBell() {
    const { notifications, unreadCount, markAsRead, markAllAsRead, removeNotification, clearAll, addNotification } = useNotifications()
    const [open, setOpen] = useState(false)

    const requestPermission = async () => {
        if ('Notification' in window && Notification.permission === 'default') {
            await Notification.requestPermission()
        }
    }

    React.useEffect(() => { requestPermission() }, [])

    const typeIcon = (type: NotificationType) => {
        if (type === 'success') return 'check_circle'
        if (type === 'error') return 'error'
        if (type === 'warning') return 'warning'
        return 'info'
    }

    const typeBg = (type: NotificationType) => {
        if (type === 'success') return 'bg-rag-green'
        if (type === 'error') return 'bg-rag-red'
        if (type === 'warning') return 'bg-rag-amber'
        return 'bg-rag-blue'
    }

    return (
        <div className="relative">
            <button
                type="button"
                onClick={() => setOpen((prev) => !prev)}
                className="relative w-9 h-9 border border-accent-silver/20 flex items-center justify-center text-silver-bright bg-charcoal-dark hover:bg-secondary transition-colors"
                aria-label={`Notifications — ${unreadCount} unread`}
                aria-expanded={open}
                aria-haspopup="true"
            >
                <span className="material-symbols-outlined text-[20px]">notifications</span>
                {unreadCount > 0 && (
                    <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] bg-rag-red border-2 border-charcoal-dark flex items-center justify-center text-[9px] font-black text-white rounded-full px-1">
                        {unreadCount > 99 ? '99+' : unreadCount}
                    </span>
                )}
            </button>

            <AnimatePresence>
                {open && (
                    <>
                        <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
                        <motion.div
                            initial={{ opacity: 0, y: -8, scale: 0.95 }}
                            animate={{ opacity: 1, y: 0, scale: 1 }}
                            exit={{ opacity: 0, y: -8, scale: 0.95 }}
                            transition={{ duration: 0.15 }}
                            className="absolute right-0 top-11 z-50 w-[360px] bg-secondary border-4 border-black shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] flex flex-col"
                        >
                            {/* Header */}
                            <div className="flex items-center justify-between px-4 py-3 border-b-4 border-black">
                                <div className="flex items-center gap-2">
                                    <span className="material-symbols-outlined text-[16px] text-silver-bright">notifications</span>
                                    <span className="text-[11px] font-black uppercase tracking-widest text-silver-bright">Notifications</span>
                                    {unreadCount > 0 && (
                                        <span className="bg-rag-red text-white text-[9px] font-black px-1.5 py-0.5 rounded-full">{unreadCount}</span>
                                    )}
                                </div>
                                <div className="flex items-center gap-2">
                                    {unreadCount > 0 && (
                                        <button
                                            type="button"
                                            onClick={markAllAsRead}
                                            className="text-[9px] font-black uppercase tracking-widest text-silver/60 hover:text-silver-bright transition-colors"
                                        >
                                            Mark all read
                                        </button>
                                    )}
                                    {notifications.length > 0 && (
                                        <button
                                            type="button"
                                            onClick={clearAll}
                                            className="text-[9px] font-black uppercase tracking-widest text-silver/60 hover:text-rag-red transition-colors"
                                        >
                                            Clear all
                                        </button>
                                    )}
                                </div>
                            </div>

                            {/* List */}
                            <div className="overflow-y-auto max-h-[400px] flex flex-col">
                                {notifications.length === 0 ? (
                                    <div className="flex flex-col items-center justify-center py-12 gap-3 text-silver/40">
                                        <span className="material-symbols-outlined text-[40px]">notifications_none</span>
                                        <span className="text-[10px] font-black uppercase tracking-widest">No notifications</span>
                                    </div>
                                ) : (
                                    <AnimatePresence initial={false}>
                                        {notifications.map((n) => (
                                            <motion.div
                                                key={n.id}
                                                initial={{ opacity: 0, height: 0 }}
                                                animate={{ opacity: 1, height: 'auto' }}
                                                exit={{ opacity: 0, height: 0 }}
                                                className={`flex items-start gap-3 px-4 py-3 border-b border-accent-silver/10 cursor-pointer hover:bg-charcoal-dark transition-colors group relative ${!n.read ? 'bg-charcoal-dark/50' : ''}`}
                                                onClick={() => markAsRead(n.id)}
                                            >
                                                <span className={`material-symbols-outlined text-[16px] mt-0.5 shrink-0 ${typeBg(n.type)} p-1 text-black`}>
                                                    {typeIcon(n.type)}
                                                </span>
                                                <div className="flex-1 min-w-0">
                                                    <div className="flex items-center justify-between gap-2">
                                                        <span className="text-[11px] font-black uppercase tracking-tight text-silver-bright truncate">{n.title}</span>
                                                        {!n.read && <span className="w-2 h-2 rounded-full bg-rag-red shrink-0" />}
                                                    </div>
                                                    <p className="text-[10px] text-silver/70 font-medium mt-0.5 leading-relaxed">{n.message}</p>
                                                    <span className="text-[9px] text-silver/40 font-black uppercase tracking-widest mt-1 block">{timeAgo(n.timestamp)}</span>
                                                </div>
                                                <button
                                                    type="button"
                                                    onClick={(e) => { e.stopPropagation(); removeNotification(n.id) }}
                                                    className="opacity-0 group-hover:opacity-100 shrink-0 text-silver/40 hover:text-rag-red transition-colors"
                                                    aria-label="Dismiss notification"
                                                >
                                                    <span className="material-symbols-outlined text-[14px]">close</span>
                                                </button>
                                            </motion.div>
                                        ))}
                                    </AnimatePresence>
                                )}
                            </div>
                        </motion.div>
                    </>
                )}
            </AnimatePresence>
        </div>
    )
}
