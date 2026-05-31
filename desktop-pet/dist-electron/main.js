"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
const electron_1 = require("electron");
const path = __importStar(require("path"));
let petWindow = null;
let summaryWindow = null;
let mouseDownWinPos = null;
const PET_WIDTH = 220;
const PET_HEIGHT = 380;
const SUMMARY_WIDTH = 420;
const SUMMARY_HEIGHT = 620;
function createPetWindow() {
    const display = electron_1.screen.getPrimaryDisplay();
    const { width: screenW, height: screenH } = display.workAreaSize;
    petWindow = new electron_1.BrowserWindow({
        width: PET_WIDTH,
        height: PET_HEIGHT,
        x: screenW - PET_WIDTH - 40,
        y: screenH - PET_HEIGHT - 40,
        frame: false,
        transparent: true,
        alwaysOnTop: true,
        resizable: false,
        skipTaskbar: true,
        hasShadow: false,
        focusable: true,
        show: false,
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            contextIsolation: true,
            nodeIntegration: false,
        },
    });
    petWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
    petWindow.setIgnoreMouseEvents(false);
    petWindow.once('ready-to-show', () => {
        petWindow?.show();
    });
    petWindow.webContents.once('did-fail-load', () => {
        petWindow?.show();
    });
    const isDev = !electron_1.app.isPackaged;
    if (isDev) {
        petWindow.loadURL('http://localhost:5173/#pet');
    }
    else {
        petWindow.loadFile(path.join(__dirname, '../dist/index.html'), { hash: 'pet' });
    }
    petWindow.on('closed', () => {
        petWindow = null;
    });
}
function createSummaryWindow() {
    if (summaryWindow) {
        summaryWindow.show();
        summaryWindow.focus();
        return;
    }
    const display = electron_1.screen.getPrimaryDisplay();
    const { width: screenW, height: screenH } = display.workAreaSize;
    summaryWindow = new electron_1.BrowserWindow({
        width: SUMMARY_WIDTH,
        height: SUMMARY_HEIGHT,
        x: screenW - SUMMARY_WIDTH - PET_WIDTH - 60,
        y: screenH - SUMMARY_HEIGHT - 40,
        frame: false,
        transparent: true,
        alwaysOnTop: true,
        resizable: false,
        skipTaskbar: true,
        hasShadow: true,
        focusable: true,
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            contextIsolation: true,
            nodeIntegration: false,
        },
    });
    summaryWindow.setVisibleOnAllWorkspaces(true);
    summaryWindow.once('ready-to-show', () => {
        summaryWindow?.show();
    });
    summaryWindow.webContents.once('did-fail-load', () => {
        summaryWindow?.show();
    });
    const isDev = !electron_1.app.isPackaged;
    if (isDev) {
        summaryWindow.loadURL('http://localhost:5173/#summary');
    }
    else {
        summaryWindow.loadFile(path.join(__dirname, '../dist/index.html'), { hash: 'summary' });
    }
    summaryWindow.on('closed', () => {
        summaryWindow = null;
    });
}
function closeSummaryWindow() {
    if (summaryWindow) {
        summaryWindow.close();
        summaryWindow = null;
    }
}
function snapToNearestCorner() {
    if (!petWindow)
        return;
    const { width, height } = electron_1.screen.getPrimaryDisplay().workAreaSize;
    const [x, y] = petWindow.getPosition();
    const centerX = x + PET_WIDTH / 2;
    const centerY = y + PET_HEIGHT / 2;
    const corners = [
        { x: 0, y: 0 },
        { x: width - PET_WIDTH, y: 0 },
        { x: 0, y: height - PET_HEIGHT },
        { x: width - PET_WIDTH, y: height - PET_HEIGHT },
    ];
    let nearest = corners[0];
    let minDist = Infinity;
    for (const corner of corners) {
        const dist = Math.sqrt((centerX - (corner.x + PET_WIDTH / 2)) ** 2 +
            (centerY - (corner.y + PET_HEIGHT / 2)) ** 2);
        if (dist < minDist) {
            minDist = dist;
            nearest = corner;
        }
    }
    petWindow.setPosition(nearest.x, nearest.y);
}
electron_1.app.whenReady().then(() => {
    createPetWindow();
    electron_1.ipcMain.on('open-summary', () => {
        createSummaryWindow();
    });
    electron_1.ipcMain.on('close-summary', () => {
        closeSummaryWindow();
    });
    electron_1.ipcMain.on('toggle-summary', () => {
        if (summaryWindow) {
            closeSummaryWindow();
        }
        else {
            createSummaryWindow();
        }
    });
    electron_1.ipcMain.on('mouse-down-on-pet', () => {
        if (!petWindow)
            return;
        mouseDownWinPos = petWindow.getPosition();
    });
    electron_1.ipcMain.on('mouse-up-on-pet', () => {
        if (!petWindow || !mouseDownWinPos)
            return;
        const [currentX, currentY] = petWindow.getPosition();
        const [downX, downY] = mouseDownWinPos;
        mouseDownWinPos = null;
        const moved = Math.abs(currentX - downX) > 5 || Math.abs(currentY - downY) > 5;
        if (!moved) {
            petWindow.webContents.send('pet-clicked');
            return;
        }
        snapToNearestCorner();
    });
});
electron_1.app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        electron_1.app.quit();
    }
});
electron_1.app.on('activate', () => {
    if (!petWindow) {
        createPetWindow();
    }
});
