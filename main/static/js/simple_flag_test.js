/**
 * Simple Flag Test Script
 * Just tests right-click detection on the PK game grid
 */

console.log('🚩 Simple Flag Test Script loaded');

document.addEventListener('DOMContentLoaded', function() {
    console.log('🚩 DOM loaded, setting up simple right-click test');
    
    // Test if we can find the game view
    const gameView = document.getElementById('game-view');
    console.log('🚩 Game view element:', gameView);
    
    if (gameView) {
        console.log('🚩 Found game view, adding right-click listener');
        
        // Add right-click listener to prevent default context menu
        gameView.addEventListener('contextmenu', function(e) {
            console.log('🚩 RIGHT-CLICK DETECTED!', e);
            e.preventDefault();
            e.stopPropagation();
            
            // Show a simple alert for now
            alert('Right-click detected on game view! Flag system working.');
            
            return false;
        });
        
        // Also try on the container
        const container = document.querySelector('.game-view-container');
        if (container) {
            console.log('🚩 Found game view container, adding right-click listener');
            container.addEventListener('contextmenu', function(e) {
                console.log('🚩 RIGHT-CLICK ON CONTAINER DETECTED!', e);
                e.preventDefault();
                e.stopPropagation();
                
                alert('Right-click detected on container! Flag system working.');
                return false;
            });
        }
    } else {
        console.error('🚩 Could not find game view element!');
    }
    
    // Test general right-click detection
    document.addEventListener('contextmenu', function(e) {
        console.log('🚩 General right-click detected on:', e.target);
        
        // Check if it's on our game elements
        const isGameElement = e.target.closest('#game-view, .game-view-container, .game-grid');
        if (isGameElement) {
            console.log('🚩 Right-click is on a game element!');
            e.preventDefault();
            
            // Create a simple context menu
            showSimpleMenu(e.clientX, e.clientY);
            return false;
        }
    });
});

function showSimpleMenu(x, y) {
    // Remove any existing menu
    const existingMenu = document.querySelector('.simple-flag-menu');
    if (existingMenu) {
        existingMenu.remove();
    }
    
    // Create simple menu
    const menu = document.createElement('div');
    menu.className = 'simple-flag-menu';
    menu.style.cssText = `
        position: fixed;
        left: ${x}px;
        top: ${y}px;
        background: rgba(0, 0, 0, 0.9);
        border: 2px solid #ff4444;
        border-radius: 8px;
        padding: 10px;
        z-index: 10000;
        color: white;
        font-family: Arial, sans-serif;
    `;
    
    menu.innerHTML = `
        <div style="font-weight: bold; margin-bottom: 10px;">🚩 Flag Menu Test</div>
        <div style="padding: 5px; cursor: pointer; border-radius: 4px;" onmouseover="this.style.background='#333'" onmouseout="this.style.background='transparent'" onclick="alert('Flag placement would happen here!'); document.querySelector('.simple-flag-menu').remove();">
            Place Flag
        </div>
        <div style="padding: 5px; cursor: pointer; border-radius: 4px;" onmouseover="this.style.background='#333'" onmouseout="this.style.background='transparent'" onclick="document.querySelector('.simple-flag-menu').remove();">
            Cancel
        </div>
    `;
    
    document.body.appendChild(menu);
    
    // Remove menu when clicking elsewhere
    setTimeout(() => {
        const removeOnClick = (e) => {
            if (!menu.contains(e.target)) {
                menu.remove();
                document.removeEventListener('click', removeOnClick);
            }
        };
        document.addEventListener('click', removeOnClick);
    }, 100);
}

console.log('🚩 Simple Flag Test Script setup complete');
