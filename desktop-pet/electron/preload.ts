import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('electronAPI', {
    openSummary: () => ipcRenderer.send('open-summary'),
    closeSummary: () => ipcRenderer.send('close-summary'),
    toggleSummary: () => ipcRenderer.send('toggle-summary'),
    notifyMouseDown: () => ipcRenderer.send('mouse-down-on-pet'),
    notifyMouseUp: () => ipcRenderer.send('mouse-up-on-pet'),
    onPetClicked: (callback: () => void) => {
        const handler = () => callback()
        ipcRenderer.on('pet-clicked', handler)
        return () => ipcRenderer.removeListener('pet-clicked', handler)
    },
})
