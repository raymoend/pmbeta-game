/**
 * RPG Game WebSocket Client
 * Handles real-time communication for movement, combat, trading, and chat
 */

class RPGWebSocketClient {
    constructor(options = {}) {
        // Accept both { url, reconnectAttempts, reconnectDelay } and legacy { wsUrl, maxReconnectAttempts, reconnectInterval }
        this.wsUrl = options.url || options.wsUrl || `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/game/`;
        this.reconnectInterval = options.reconnectDelay || options.reconnectInterval || 3000;
        this.maxReconnectAttempts = options.reconnectAttempts || options.maxReconnectAttempts || 5;
        this.pingInterval = options.pingInterval || 30000;
        
        this.ws = null;
        this.reconnectAttempts = 0;
        this.connected = false; // internal connection state
        this.pingTimer = null;
        
        // Event handlers
        this.eventHandlers = new Map();
        this.messageQueue = [];
        
        // Initialize connection
        this.connect();
        
        // Handle page visibility for connection management
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible' && !this.connected) {
                this.connect();
            }
        });
    }

    // Compatibility shim with dashboard/map usage
    addEventListener(event, handler) { this.on(event, handler); }
    removeEventListener(event, handler) { this.off(event, handler); }
    isConnected() { return this.connected; }
    
    /**
     * Establish WebSocket connection
     */
    connect() {
        try {
            this.ws = new WebSocket(this.wsUrl);
            this.setupEventListeners();
        } catch (error) {
            console.error('WebSocket connection error:', error);
            this.handleReconnect();
        }
    }
    
    /**
     * Setup WebSocket event listeners
     */
    setupEventListeners() {
this.ws.onopen = (event) => {
            console.log('WebSocket connected');
            this.connected = true;
            this.reconnectAttempts = 0;
            
            // Send queued messages
            this.flushMessageQueue();
            
            // Start ping timer
            this.startPingTimer();
            
            // Trigger connected event
            this.trigger('connected', { event });
        };
        
        this.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleMessage(data);
            } catch (error) {
                console.error('WebSocket message parse error:', error);
            }
        };
        
this.ws.onclose = (event) => {
            console.log('WebSocket disconnected:', event.code, event.reason);
            this.connected = false;
            this.stopPingTimer();
            
            // Trigger disconnected event
            this.trigger('disconnected', { event });
            
            // Attempt reconnection if not a clean close
            if (event.code !== 1000) {
                this.handleReconnect();
            }
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.trigger('error', { error });
        };
    }
    
    /**
     * Handle incoming WebSocket messages
     */
    handleMessage(data) {
        const { type, data: messageData } = data;
        
        // Route message to appropriate handler
        switch (type) {
            case 'initial_data':
                this.trigger('initial_data', messageData);
                break;
                
            case 'character_moved':
                this.trigger('character_moved', messageData);
                break;
                
            case 'chat_message':
                this.trigger('chat_message', messageData);
                break;
                
            case 'combat_update':
                this.trigger('combat_update', messageData);
                break;
                
            case 'trade_request':
                this.trigger('trade_request', messageData);
                break;
                
            case 'trade_response':
                this.trigger('trade_response', messageData);
                break;
                
            case 'skill_result':
                this.trigger('skill_result', messageData);
                break;
                
            case 'inventory':
                this.trigger('inventory_update', messageData);
                break;
                
            case 'character':
                // Character HUD snapshot (level/xp/hp/gold/etc.)
                this.trigger('character_updated', messageData);
                break;
                
            case 'character_stats':
                this.trigger('character_stats', messageData);
                break;
                
            case 'error':
                this.trigger('server_error', messageData);
                break;
                
            default:
                console.warn('Unknown message type:', type);
        }
    }
    
    /**
     * Send message to server
     */
    send(type, data = {}) {
        const message = {
            type: type,
            data: data
        };
        
if (this.connected) {
            this.ws.send(JSON.stringify(message));
        } else {
            // Queue message for later
            this.messageQueue.push(message);
        }
    }
    
    /**
     * Send queued messages
     */
    flushMessageQueue() {
        while (this.messageQueue.length > 0) {
            const message = this.messageQueue.shift();
            this.ws.send(JSON.stringify(message));
        }
    }
    
    /**
     * Handle reconnection attempts
     */
    handleReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Reconnecting... Attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);
            
            setTimeout(() => {
                this.connect();
            }, this.reconnectInterval);
        } else {
            console.error('Max reconnection attempts reached');
            this.trigger('max_reconnect_attempts');
        }
    }
    
    /**
     * Start ping timer to keep connection alive
     */
    startPingTimer() {
        this.pingTimer = setInterval(() => {
if (this.connected) {
                this.send('ping', { timestamp: Date.now() });
            }
        }, this.pingInterval);
    }
    
    /**
     * Stop ping timer
     */
    stopPingTimer() {
        if (this.pingTimer) {
            clearInterval(this.pingTimer);
            this.pingTimer = null;
        }
    }
    
    /**
     * Register event handler
     */
    on(event, handler) {
        if (!this.eventHandlers.has(event)) {
            this.eventHandlers.set(event, []);
        }
        this.eventHandlers.get(event).push(handler);
    }
    
    /**
     * Unregister event handler
     */
    off(event, handler) {
        if (this.eventHandlers.has(event)) {
            const handlers = this.eventHandlers.get(event);
            const index = handlers.indexOf(handler);
            if (index > -1) {
                handlers.splice(index, 1);
            }
        }
    }
    
    /**
     * Trigger event
     */
    trigger(event, data = {}) {
        if (this.eventHandlers.has(event)) {
            this.eventHandlers.get(event).forEach(handler => {
                try {
                    handler(data);
                } catch (error) {
                    console.error('Event handler error:', error);
                }
            });
        }
    }
    
    /**
     * Game-specific methods
     */
    
    // Movement
    moveCharacter(latitude, longitude) {
        this.send('move', {
            target: { lat: latitude, lon: longitude }
        });
    }
    
    // Chat
    sendChatMessage(message, channel = 'global') {
        this.send('chat', {
            message: message,
            channel: channel
        });
    }
    
    // Combat
    attackMonster(monsterId) {
        this.send('attack', {
            target_type: 'monster',
            target_id: monsterId
        });
    }
    
    attackCharacter(characterId) {
        this.send('attack', {
            target_type: 'character',
            target_id: characterId
        });
    }
    
    fleeFromCombat(combatId) {
        this.send('flee', {
            combat_id: combatId
        });
    }
    
    useSkill(skillId, targetId = null) {
        this.send('use_skill', {
            skill_id: skillId,
            target_id: targetId
        });
    }
    
    // Trading
    sendTradeRequest(targetCharacterId, offeredItems, requestedItems) {
        this.send('trade_request', {
            target_character_id: targetCharacterId,
            offered_items: offeredItems,
            requested_items: requestedItems
        });
    }
    
    respondToTrade(tradeId, response) {
        this.send('trade_respond', {
            trade_id: tradeId,
            response: response // 'accept' or 'decline'
        });
    }
    
    // Data requests
    requestGameData() {
        this.send('get_game_data');
    }
    
    requestInventory() {
        this.send('get_inventory');
    }
    
    requestCharacterStats() {
        this.send('get_character_stats');
    }
    
    /**
     * Close connection
     */
disconnect() {
        this.stopPingTimer();
        if (this.ws && this.connected) {
            this.ws.close(1000, 'Client disconnect');
        }
    }
    
    /**
     * Get connection status
     */
getConnectionStatus() {
        return {
            connected: this.connected,
            reconnectAttempts: this.reconnectAttempts,
            queuedMessages: this.messageQueue.length
        };
    }
}

// Export for use in other scripts
window.RPGWebSocketClient = RPGWebSocketClient;
