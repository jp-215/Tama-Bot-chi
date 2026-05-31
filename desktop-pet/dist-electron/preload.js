"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const electron_1 = require("electron");
electron_1.contextBridge.exposeInMainWorld('electronAPI', {
    openSummary: () => electron_1.ipcRenderer.send('open-summary'),
    closeSummary: () => electron_1.ipcRenderer.send('close-summary'),
    toggleSummary: () => electron_1.ipcRenderer.send('toggle-summary'),
    notifyMouseDown: () => electron_1.ipcRenderer.send('mouse-down-on-pet'),
    notifyMouseUp: () => electron_1.ipcRenderer.send('mouse-up-on-pet'),
    onPetClicked: (callback) => {
        const handler = () => callback();
        electron_1.ipcRenderer.on('pet-clicked', handler);
        return () => electron_1.ipcRenderer.removeListener('pet-clicked', handler);
    },
});
