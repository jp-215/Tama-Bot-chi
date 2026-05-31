/// <reference types="vite/client" />

interface ElectronAPI {
    openSummary: () => void
    closeSummary: () => void
    toggleSummary: () => void
    notifyMouseDown: () => void
    notifyMouseUp: () => void
    onPetClicked: (callback: () => void) => () => void
}

interface Window {
    electronAPI?: ElectronAPI
}
