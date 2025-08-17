/**
 * GameDashboard - Main controller for The Shattered Realm
 * Coordinates all game systems: UI, WebSocket, API, Map, Combat, etc.
 */
class GameDashboard {
    constructor(options = {}) {
        this.options = options;
        this.character = options.character || {};
        this.mapboxToken = options.mapboxAccessToken;
        
        // Initialize subsystems
        this.api = null;
        this.websocket = null;
        this.map = null;
        this.combat = null;
        
        // UI state
        this.isLoading = true;
        this.connectionStatus = 'disconnected';
        this.activeChat = 'global';
        this.notifications = [];
        
        // Game state
        this.inCombat = false;
        this.currentQuests = [];
        this.inventory = [];
        
        this.init();
    }
    
    async init() {
        try {
            this.showLoadingProgress(10, 'Initializing systems...');
            
            // Initialize API client
            this.api = new RPGGameAPI({
                baseUrl: window.location.origin + '/api',
                csrfToken: document.querySelector('meta[name="csrf-token"]')?.getAttribute('content')
            });
            this.showLoadingProgress(20, 'API connected...');
            
            // Initialize WebSocket client
            this.websocket = new RPGWebSocketClient({
                url: this.getWebSocketUrl(),
                reconnectAttempts: 5,
                reconnectDelay: 1000
            });
            this.showLoadingProgress(40, 'WebSocket connecting...');
            
            // Setup WebSocket event handlers
            this.setupWebSocketEvents();
            
            // Wait for WebSocket connection
            await this.waitForWebSocketConnection();
            this.showLoadingProgress(60, 'Real-time connection established...');
            
            // Initialize map
            if (this.mapboxToken) {
                this.map = new GameMap({
                    mapboxToken: this.mapboxToken,
                    container: 'map',
                    character: this.character,
                    api: this.api,
                    websocket: this.websocket
                });
                this.showLoadingProgress(80, 'Map loading...');
            }
            
            // Initialize UI components
            this.setupUIEventListeners();
            this.showLoadingProgress(90, 'Setting up interface...');
            
            // Load initial game data
            await this.loadInitialData();
            this.showLoadingProgress(100, 'Complete!');
            
            // Hide loading screen and show game
            setTimeout(() => {
                this.hideLoadingScreen();
                this.isLoading = false;
            }, 500);
            
        } catch (error) {
            console.error('Failed to initialize game:', error);
            this.showError('Failed to load game. Please refresh the page.');
        }
    }
    
    setupWebSocketEvents() {
        // Connection events
        this.websocket.addEventListener('connected', () => {
            this.updateConnectionStatus('connected');
            this.showNotification('Connected to The Shattered Realm', 'success');
        });
        
        this.websocket.addEventListener('disconnected', () => {
            this.updateConnectionStatus('disconnected');
            this.showNotification('Connection lost. Attempting to reconnect...', 'warning');
        });
        
        this.websocket.addEventListener('reconnected', () => {
            this.updateConnectionStatus('connected');
            this.showNotification('Reconnected successfully!', 'success');
            this.loadInitialData(); // Refresh data after reconnection
        });
        
        // Game events
        this.websocket.addEventListener('character_updated', (data) => {
            this.updateCharacterStats(data);
        });
        
        this.websocket.addEventListener('combat_started', (data) => {
            this.startCombat(data);
        });
        
        this.websocket.addEventListener('combat_ended', (data) => {
            this.endCombat(data);
        });
        
        this.websocket.addEventListener('combat_update', (data) => {
            this.updateCombat(data);
        });
        
        this.websocket.addEventListener('chat_message', (data) => {
            this.addChatMessage(data);
        });
        
        this.websocket.addEventListener('quest_completed', (data) => {
            this.handleQuestCompleted(data);
        });
        
        this.websocket.addEventListener('quest_updated', (data) => {
            this.updateQuest(data);
        });
        
        this.websocket.addEventListener('trade_request', (data) => {
            this.handleTradeRequest(data);
        });
        
        this.websocket.addEventListener('notification', (data) => {
            this.showNotification(data.message, data.type || 'info');
        });
    }
    
    setupUIEventListeners() {
        // Panel toggles
        document.querySelectorAll('.panel-toggle').forEach(button => {
            button.addEventListener('click', (e) => {
                const target = e.target.getAttribute('data-target');
                this.togglePanel(target);
            });
        });
        
        // Map controls
        const centerMapBtn = document.getElementById('center-map-btn');
        if (centerMapBtn) {
            centerMapBtn.addEventListener('click', () => {
                this.map?.centerOnCharacter();
            });
        }
        
        const updateLocationBtn = document.getElementById('update-location-btn');
        if (updateLocationBtn) {
            updateLocationBtn.addEventListener('click', () => {
                this.updateLocation();
            });
        }
        
        // Combat controls
        const attackBtn = document.getElementById('attack-btn');
        if (attackBtn) {
            attackBtn.addEventListener('click', () => {
                this.attack();
            });
        }
        
        const fleeBtn = document.getElementById('flee-btn');
        if (fleeBtn) {
            fleeBtn.addEventListener('click', () => {
                this.flee();
            });
        }
        
        // Chat controls
        const chatInput = document.getElementById('chat-input');
        const sendChatBtn = document.getElementById('send-chat-btn');
        
        if (chatInput && sendChatBtn) {
            chatInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.sendChatMessage();
                }
            });
            
            sendChatBtn.addEventListener('click', () => {
                this.sendChatMessage();
            });
        }
        
        // Chat channel switching
        document.querySelectorAll('.chat-channel').forEach(button => {
            button.addEventListener('click', (e) => {
                const channel = e.target.getAttribute('data-channel');
                this.switchChatChannel(channel);
            });
        });
        
        // Quest controls
        const generateQuestBtn = document.getElementById('generate-quest-btn');
        if (generateQuestBtn) {
            generateQuestBtn.addEventListener('click', () => {
                this.showQuestModal();
            });
        }
        
        // Modal controls
        this.setupModalControls();
        
        // Header buttons
        const logoutBtn = document.getElementById('logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => {
                this.logout();
            });
        }
    }
    
    setupModalControls() {
        // Quest modal
        const questModal = document.getElementById('quest-modal');
        const closeQuestModal = document.getElementById('close-quest-modal');
        const cancelQuestBtn = document.getElementById('cancel-quest-btn');
        const confirmQuestBtn = document.getElementById('confirm-quest-btn');
        
        if (closeQuestModal) closeQuestModal.addEventListener('click', () => this.hideModal('quest-modal'));
        if (cancelQuestBtn) cancelQuestBtn.addEventListener('click', () => this.hideModal('quest-modal'));
        if (confirmQuestBtn) confirmQuestBtn.addEventListener('click', () => this.generateQuest());
        
        // Trade modal
        const closeTradeModal = document.getElementById('close-trade-modal');
        const declineTradeBtn = document.getElementById('decline-trade-btn');
        const acceptTradeBtn = document.getElementById('accept-trade-btn');
        
        if (closeTradeModal) closeTradeModal.addEventListener('click', () => this.hideModal('trade-modal'));
        if (declineTradeBtn) declineTradeBtn.addEventListener('click', () => this.declineTrade());
        if (acceptTradeBtn) acceptTradeBtn.addEventListener('click', () => this.acceptTrade());
        
        // Close modals on background click
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.hideModal(modal.id);
                }
            });
        });
    }
    
    async loadInitialData() {
        try {
            // Get current game status
            const gameStatus = await this.api.getGameStatus();
            if (gameStatus.success) {
                this.updateCharacterStats(gameStatus.character);
                this.currentQuests = gameStatus.quests || [];
                this.updateQuestList();
                
                // Check if in combat
                if (gameStatus.combat) {
                    this.startCombat(gameStatus.combat);
                }
            }
            
            // Load inventory
            const inventory = await this.api.getInventory();
            if (inventory.success) {
                this.inventory = inventory.items || [];
                this.updateInventoryDisplay();
            }
            
        } catch (error) {
            console.error('Failed to load initial data:', error);
        }
    }
    
    updateCharacterStats(character) {
        // Update character info in header
        const levelEl = document.getElementById('character-level');
        if (levelEl) levelEl.textContent = character.level;
        
        // Update stats panel
        const stats = ['health', 'gold', 'strength', 'defense', 'vitality', 'agility', 'intelligence'];
        stats.forEach(stat => {
            const el = document.getElementById(`character-${stat}`);
            if (el && character[stat] !== undefined) {
                el.textContent = character[stat];
            }
        });
        
        // Update health bar
        if (character.health !== undefined && character.max_health !== undefined) {
            this.updateHealthBar(character.health, character.max_health);
        }
        
        // Update experience bar
        if (character.experience !== undefined && character.experience_to_next !== undefined) {
            this.updateExperienceBar(character.experience, character.experience_to_next);
        }
    }
    
    updateHealthBar(current, max) {
        const healthBar = document.getElementById('health-bar');
        const healthText = document.getElementById('health-text');
        
        if (healthBar) {
            const percentage = (current / max) * 100;
            healthBar.style.width = `${percentage}%`;
            
            // Color based on health percentage
            if (percentage > 60) {
                healthBar.className = 'bar health-bar-fill health-good';
            } else if (percentage > 30) {
                healthBar.className = 'bar health-bar-fill health-warning';
            } else {
                healthBar.className = 'bar health-bar-fill health-critical';
            }
        }
        
        if (healthText) {
            healthText.textContent = `${current}/${max}`;
        }
    }
    
    updateExperienceBar(current, toNext) {
        const expBar = document.getElementById('exp-bar');
        const expText = document.getElementById('exp-text');
        
        if (expBar) {
            const percentage = (current / toNext) * 100;
            expBar.style.width = `${percentage}%`;
        }
        
        if (expText) {
            expText.textContent = `${current}/${toNext}`;
        }
    }
    
    startCombat(combatData) {
        this.inCombat = true;
        const combatPanel = document.getElementById('combat-panel');
        if (combatPanel) {
            combatPanel.style.display = 'block';
        }
        
        // Update enemy info
        const enemyName = document.getElementById('enemy-name');
        if (enemyName) enemyName.textContent = combatData.enemy.name;
        
        this.updateEnemyHealth(combatData.enemy.health, combatData.enemy.max_health);
        this.showNotification(`Combat started with ${combatData.enemy.name}!`, 'warning');
    }
    
    endCombat(combatData) {
        this.inCombat = false;
        const combatPanel = document.getElementById('combat-panel');
        if (combatPanel) {
            combatPanel.style.display = 'none';
        }
        
        // Clear combat log after delay
        setTimeout(() => {
            const combatLog = document.getElementById('combat-log');
            if (combatLog) combatLog.innerHTML = '';
        }, 3000);
        
        if (combatData.victory) {
            this.showNotification('Victory! You gained experience and gold.', 'success');
        } else {
            this.showNotification('You escaped from combat!', 'info');
        }
    }
    
    updateCombat(combatData) {
        // Update enemy health
        if (combatData.enemy) {
            this.updateEnemyHealth(combatData.enemy.health, combatData.enemy.max_health);
        }
        
        // Add combat message
        if (combatData.message) {
            this.addCombatMessage(combatData.message, combatData.messageType || 'info');
        }
    }
    
    updateEnemyHealth(current, max) {
        const enemyHealthBar = document.getElementById('enemy-health-bar');
        const enemyHealthText = document.getElementById('enemy-health-text');
        
        if (enemyHealthBar) {
            const percentage = (current / max) * 100;
            enemyHealthBar.style.width = `${percentage}%`;
        }
        
        if (enemyHealthText) {
            enemyHealthText.textContent = `${current}/${max}`;
        }
    }
    
    addCombatMessage(message, type = 'info') {
        const combatLog = document.getElementById('combat-log');
        if (!combatLog) return;
        
        const messageEl = document.createElement('div');
        messageEl.className = `combat-message combat-${type}`;
        messageEl.textContent = message;
        
        combatLog.appendChild(messageEl);
        combatLog.scrollTop = combatLog.scrollHeight;
        
        // Remove old messages if too many
        while (combatLog.children.length > 10) {
            combatLog.removeChild(combatLog.firstChild);
        }
    }
    
    async attack() {
        if (!this.inCombat) return;
        
        try {
            const response = await this.api.attack();
            if (!response.success) {
                this.showNotification(response.message || 'Attack failed', 'error');
            }
        } catch (error) {
            console.error('Attack failed:', error);
            this.showNotification('Attack failed', 'error');
        }
    }
    
    async flee() {
        if (!this.inCombat) return;
        
        try {
            const response = await this.api.flee();
            if (!response.success) {
                this.showNotification(response.message || 'Cannot flee', 'error');
            }
        } catch (error) {
            console.error('Flee failed:', error);
            this.showNotification('Flee failed', 'error');
        }
    }
    
    addChatMessage(data) {
        const chatMessages = document.getElementById('chat-messages');
        if (!chatMessages) return;
        
        const messageEl = document.createElement('div');
        messageEl.className = `chat-message chat-${data.channel}`;
        
        const timestamp = new Date(data.timestamp).toLocaleTimeString();
        messageEl.innerHTML = `
            <span class="message-time">[${timestamp}]</span>
            <span class="message-author">${data.author}:</span>
            <span class="message-text">${data.message}</span>
        `;
        
        chatMessages.appendChild(messageEl);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        // Remove old messages if too many
        while (chatMessages.children.length > 100) {
            chatMessages.removeChild(chatMessages.firstChild);
        }
    }
    
    sendChatMessage() {
        const chatInput = document.getElementById('chat-input');
        if (!chatInput) return;
        
        const message = chatInput.value.trim();
        if (!message) return;
        
        this.websocket.sendChatMessage(this.activeChat, message);
        chatInput.value = '';
    }
    
    switchChatChannel(channel) {
        this.activeChat = channel;
        
        // Update UI
        document.querySelectorAll('.chat-channel').forEach(btn => {
            btn.classList.remove('active');
        });
        
        document.querySelector(`[data-channel="${channel}"]`)?.classList.add('active');
    }
    
    showQuestModal() {
        this.showModal('quest-modal');
    }
    
    async generateQuest() {
        const questType = document.getElementById('quest-type')?.value || '';
        const difficulty = document.getElementById('quest-difficulty')?.value || 'normal';
        
        try {
            const response = await this.api.generateQuest({ type: questType, difficulty });
            if (response.success) {
                this.showNotification('New quest generated!', 'success');
                this.currentQuests.push(response.quest);
                this.updateQuestList();
            } else {
                this.showNotification(response.message || 'Failed to generate quest', 'error');
            }
        } catch (error) {
            console.error('Quest generation failed:', error);
            this.showNotification('Failed to generate quest', 'error');
        }
        
        this.hideModal('quest-modal');
    }
    
    updateQuestList() {
        const questList = document.getElementById('quest-list');
        if (!questList) return;
        
        if (this.currentQuests.length === 0) {
            questList.innerHTML = '<div class="no-quests">No active quests</div>';
            return;
        }
        
        questList.innerHTML = this.currentQuests.map(quest => `
            <div class="quest-item" data-quest-id="${quest.id}">
                <div class="quest-title">${quest.title}</div>
                <div class="quest-description">${quest.description}</div>
                <div class="quest-progress">
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${(quest.progress / quest.max_progress) * 100}%"></div>
                    </div>
                    <span class="progress-text">${quest.progress}/${quest.max_progress}</span>
                </div>
                <div class="quest-reward">Reward: ${quest.reward_gold} gold, ${quest.reward_exp} XP</div>
            </div>
        `).join('');
    }
    
    handleQuestCompleted(data) {
        this.showNotification(`Quest completed: ${data.quest.title}!`, 'success');
        
        // Remove from current quests
        this.currentQuests = this.currentQuests.filter(q => q.id !== data.quest.id);
        this.updateQuestList();
        
        // Update character stats (experience, gold)
        this.updateCharacterStats(data.character);
    }
    
    updateQuest(data) {
        // Update quest progress
        const questIndex = this.currentQuests.findIndex(q => q.id === data.quest.id);
        if (questIndex >= 0) {
            this.currentQuests[questIndex] = data.quest;
            this.updateQuestList();
        }
    }
    
    handleTradeRequest(data) {
        const tradeModal = document.getElementById('trade-modal');
        const tradeModalBody = document.getElementById('trade-modal-body');
        
        if (tradeModalBody) {
            tradeModalBody.innerHTML = `
                <div class="trade-info">
                    <p><strong>${data.from_player}</strong> wants to trade with you:</p>
                    <div class="trade-offer">
                        <div class="offering">
                            <h4>They offer:</h4>
                            ${data.offered_items.map(item => `<div>${item.name} x${item.quantity}</div>`).join('')}
                            ${data.offered_gold > 0 ? `<div>${data.offered_gold} gold</div>` : ''}
                        </div>
                        <div class="requesting">
                            <h4>They want:</h4>
                            ${data.requested_items.map(item => `<div>${item.name} x${item.quantity}</div>`).join('')}
                            ${data.requested_gold > 0 ? `<div>${data.requested_gold} gold</div>` : ''}
                        </div>
                    </div>
                </div>
            `;
        }
        
        this.currentTradeId = data.trade_id;
        this.showModal('trade-modal');
    }
    
    async acceptTrade() {
        if (!this.currentTradeId) return;
        
        try {
            const response = await this.api.acceptTrade(this.currentTradeId);
            if (response.success) {
                this.showNotification('Trade accepted!', 'success');
            } else {
                this.showNotification(response.message || 'Trade failed', 'error');
            }
        } catch (error) {
            console.error('Trade acceptance failed:', error);
            this.showNotification('Trade failed', 'error');
        }
        
        this.hideModal('trade-modal');
        this.currentTradeId = null;
    }
    
    async declineTrade() {
        if (!this.currentTradeId) return;
        
        try {
            await this.api.declineTrade(this.currentTradeId);
        } catch (error) {
            console.error('Trade decline failed:', error);
        }
        
        this.hideModal('trade-modal');
        this.currentTradeId = null;
    }
    
    updateInventoryDisplay() {
        const inventoryGrid = document.getElementById('inventory-grid');
        if (!inventoryGrid) return;
        
        if (this.inventory.length === 0) {
            inventoryGrid.innerHTML = '<div class="empty-inventory">No items in inventory</div>';
            return;
        }
        
        inventoryGrid.innerHTML = this.inventory.map(item => `
            <div class="inventory-item" data-item-id="${item.id}">
                <div class="item-icon">
                    <i class="fas fa-${this.getItemIcon(item.type)}"></i>
                </div>
                <div class="item-info">
                    <div class="item-name">${item.name}</div>
                    <div class="item-quantity">x${item.quantity}</div>
                </div>
            </div>
        `).join('');
        
        // Update weight display
        const totalWeight = this.inventory.reduce((sum, item) => sum + (item.weight * item.quantity), 0);
        const weightEl = document.getElementById('inventory-weight');
        if (weightEl) {
            weightEl.textContent = `${totalWeight}/50`;
        }
    }
    
    getItemIcon(itemType) {
        const icons = {
            weapon: 'sword',
            armor: 'shield-alt',
            potion: 'flask',
            food: 'drumstick-bite',
            material: 'cube',
            misc: 'box'
        };
        return icons[itemType] || 'box';
    }
    
    updateConnectionStatus(status) {
        this.connectionStatus = status;
        const indicator = document.getElementById('connection-indicator');
        const text = document.getElementById('connection-text');
        
        if (indicator) {
            indicator.className = 'fas fa-circle';
            if (status === 'connected') {
                indicator.classList.add('connected');
                if (text) text.textContent = 'Connected';
            } else if (status === 'connecting') {
                indicator.classList.add('connecting');
                if (text) text.textContent = 'Connecting...';
            } else {
                indicator.classList.add('disconnected');
                if (text) text.textContent = 'Disconnected';
            }
        }
    }
    
    async updateLocation() {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                async (position) => {
                    try {
                        const { latitude, longitude } = position.coords;
                        const response = await this.api.moveCharacter(latitude, longitude);
                        
                        if (response.success) {
                            this.character.lat = latitude;
                            this.character.lon = longitude;
                            
                            if (this.map) {
                                this.map.updateCharacterPosition(latitude, longitude);
                                this.map.centerOnCharacter();
                                this.map.loadNearbyEntities();
                            }
                            
                            this.showNotification('Location updated!', 'success');
                        } else {
                            this.showNotification(response.message || 'Failed to update location', 'error');
                        }
                    } catch (error) {
                        console.error('Location update failed:', error);
                        this.showNotification('Failed to update location', 'error');
                    }
                },
                (error) => {
                    this.showNotification('Geolocation access denied', 'warning');
                }
            );
        } else {
            this.showNotification('Geolocation not supported', 'error');
        }
    }
    
    togglePanel(targetId) {
        const content = document.getElementById(targetId);
        const button = document.querySelector(`[data-target="${targetId}"]`);
        
        if (content && button) {
            const isCollapsed = content.classList.contains('collapsed');
            
            if (isCollapsed) {
                content.classList.remove('collapsed');
                button.querySelector('i').className = 'fas fa-chevron-down';
            } else {
                content.classList.add('collapsed');
                button.querySelector('i').className = 'fas fa-chevron-right';
            }
        }
    }
    
    showModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'flex';
        }
    }
    
    hideModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'none';
        }
    }
    
    showNotification(message, type = 'info', duration = 5000) {
        const notificationsContainer = document.getElementById('notifications');
        if (!notificationsContainer) return;
        
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <i class="fas fa-${this.getNotificationIcon(type)}"></i>
                <span>${message}</span>
            </div>
            <button class="notification-close">
                <i class="fas fa-times"></i>
            </button>
        `;
        
        // Add close functionality
        notification.querySelector('.notification-close').addEventListener('click', () => {
            this.removeNotification(notification);
        });
        
        notificationsContainer.appendChild(notification);
        
        // Auto remove after duration
        setTimeout(() => {
            this.removeNotification(notification);
        }, duration);
        
        // Animate in
        setTimeout(() => {
            notification.classList.add('show');
        }, 10);
    }
    
    removeNotification(notification) {
        if (notification && notification.parentNode) {
            notification.classList.remove('show');
            setTimeout(() => {
                notification.parentNode.removeChild(notification);
            }, 300);
        }
    }
    
    getNotificationIcon(type) {
        const icons = {
            success: 'check-circle',
            error: 'exclamation-circle',
            warning: 'exclamation-triangle',
            info: 'info-circle'
        };
        return icons[type] || 'info-circle';
    }
    
    showError(message) {
        const loadingScreen = document.getElementById('loading-screen');
        if (loadingScreen) {
            loadingScreen.innerHTML = `
                <div class="loading-error">
                    <i class="fas fa-exclamation-triangle"></i>
                    <div class="error-message">${message}</div>
                    <button onclick="location.reload()" class="btn btn-primary">Reload Game</button>
                </div>
            `;
        }
    }
    
    showLoadingProgress(percentage, message) {
        const progressBar = document.getElementById('loading-progress-bar');
        const loadingText = document.querySelector('.loading-text');
        
        if (progressBar) {
            progressBar.style.width = `${percentage}%`;
        }
        
        if (loadingText) {
            loadingText.textContent = message;
        }
    }
    
    hideLoadingScreen() {
        const loadingScreen = document.getElementById('loading-screen');
        const gameContainer = document.getElementById('game-container');
        
        if (loadingScreen) {
            loadingScreen.style.opacity = '0';
            setTimeout(() => {
                loadingScreen.style.display = 'none';
            }, 500);
        }
        
        if (gameContainer) {
            gameContainer.classList.remove('hidden');
        }
    }
    
    getWebSocketUrl() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        return `${protocol}//${window.location.host}/ws/game/`;
    }
    
    waitForWebSocketConnection() {
        return new Promise((resolve, reject) => {
            if (this.websocket.isConnected()) {
                resolve();
                return;
            }
            
            const timeout = setTimeout(() => {
                reject(new Error('WebSocket connection timeout'));
            }, 10000);
            
            const checkConnection = () => {
                if (this.websocket.isConnected()) {
                    clearTimeout(timeout);
                    resolve();
                } else {
                    setTimeout(checkConnection, 100);
                }
            };
            
            checkConnection();
        });
    }
    
    logout() {
        if (confirm('Are you sure you want to logout?')) {
            window.location.href = '/logout/';
        }
    }
}

// Make available globally
window.GameDashboard = GameDashboard;
