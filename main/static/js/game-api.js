/**
 * RPG Game API Client
 * Handles HTTP requests to the game backend
 */

class RPGGameAPI {
    constructor(options = {}) {
        this.baseUrl = options.baseUrl || '/api/rpg/';
        this.headers = {
            'Content-Type': 'application/json',
            'X-CSRFToken': this.getCSRFToken(),
            ...options.headers
        };
    }
    
    /**
     * Get CSRF token from cookie or meta tag
     */
    getCSRFToken() {
        // Try to get from cookie first
        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];
            
        if (cookieValue) return cookieValue;
        
        // Try to get from meta tag
        const metaTag = document.querySelector('meta[name=csrf-token]');
        return metaTag ? metaTag.getAttribute('content') : '';
    }
    
    /**
     * Make HTTP request
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const config = {
            headers: { ...this.headers, ...options.headers },
            ...options
        };
        
        try {
            const response = await fetch(url, config);
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error(`API request failed: ${endpoint}`, error);
            throw error;
        }
    }
    
    /**
     * GET request
     */
    async get(endpoint, params = {}) {
        const url = new URL(`${this.baseUrl}${endpoint}`, window.location.origin);
        Object.keys(params).forEach(key => {
            if (params[key] !== null && params[key] !== undefined) {
                url.searchParams.append(key, params[key]);
            }
        });
        
        return this.request(url.pathname + url.search, { method: 'GET' });
    }
    
    /**
     * POST request
     */
    async post(endpoint, data = {}) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }
    
    /**
     * PUT request
     */
    async put(endpoint, data = {}) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }
    
    /**
     * DELETE request
     */
    async delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    }
    
    /**
     * Game-specific API methods
     */
    
    // Game Status
    async getGameStatus() {
        return this.get('game-status/');
    }
    
    // Character Movement
    async moveCharacter(latitude, longitude) {
        return this.post('move/', { latitude, longitude });
    }
    
    // Combat
    async attackMonster(monsterId) {
        return this.post('attack/', { monster_id: monsterId });
    }
    
    async fleeFromCombat(combatId) {
        return this.post('flee/', { combat_id: combatId });
    }
    
    // Quests
    async getQuests() {
        return this.get('quests/');
    }
    
    async startQuest(questType, difficulty = 'normal') {
        return this.post('quest/start/', {
            quest_type: questType,
            difficulty: difficulty
        });
    }
    
    // Trading
    async createTrade(targetCharacterId, offeredItems = [], requestedItems = [], goldOffered = 0, goldRequested = 0) {
        return this.post('trade/create/', {
            target_character_id: targetCharacterId,
            offered_items: offeredItems,
            requested_items: requestedItems,
            gold_offered: goldOffered,
            gold_requested: goldRequested
        });
    }
    
    async respondToTrade(tradeId, response) {
        return this.post('trade/respond/', {
            trade_id: tradeId,
            response: response // 'accept' or 'decline'
        });
    }
    
    // Map
    async getMapData(zoom = 15) {
        return this.get('map/', { zoom });
    }

    // Territories
    async getTerritories() {
        return this.get('territories/');
    }

    async travelToTerritory(territoryId) {
        return this.post('territory/travel/', { territory_id: territoryId });
    }
    
    // Inventory
    async getInventory() {
        return this.get('inventory/');
    }
    
    // Skills
    async getSkills() {
        return this.get('skills/');
    }
    
    /**
     * Utility methods
     */
    
    // Format error messages
    formatError(error) {
        if (typeof error === 'string') {
            return error;
        }
        return error.message || 'An unknown error occurred';
    }
    
    // Handle API errors with user feedback
    handleError(error, context = '') {
        const message = this.formatError(error);
        console.error(`API Error${context ? ` (${context})` : ''}:`, message);
        
        // Show user notification (if notification system exists)
        if (window.showNotification) {
            window.showNotification('error', message);
        }
        
        return message;
    }
    
    // Retry failed requests
    async retryRequest(requestFn, maxRetries = 3, delay = 1000) {
        for (let attempt = 1; attempt <= maxRetries; attempt++) {
            try {
                return await requestFn();
            } catch (error) {
                if (attempt === maxRetries) {
                    throw error;
                }
                
                console.warn(`Request attempt ${attempt} failed, retrying in ${delay}ms...`);
                await new Promise(resolve => setTimeout(resolve, delay));
                delay *= 2; // Exponential backoff
            }
        }
    }
}

/**
 * Global API instance
 */
const gameAPI = new RPGGameAPI();

// Export for use in other scripts
window.RPGGameAPI = RPGGameAPI;
window.gameAPI = gameAPI;
