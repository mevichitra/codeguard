// Performance Issues and Memory Leaks Example

// ISSUE: O(n³) complexity - very inefficient
function findTriplets(arr) {
    let result = [];
    for (let i = 0; i < arr.length; i++) {
        for (let j = 0; j < arr.length; j++) {
            for (let k = 0; k < arr.length; k++) {
                if (arr[i] + arr[j] + arr[k] === 0) {
                    result.push([arr[i], arr[j], arr[k]]);
                }
            }
        }
    }
    return result;
}

// ISSUE: Memory leak - global cache never cleaned
let globalCache = {};
let eventListeners = [];

function cacheData(key, value) {
    globalCache[key] = value; // Never cleaned up
}

function addEventHandler(element, event, handler) {
    element.addEventListener(event, handler);
    eventListeners.push({element, event, handler}); // Never removed
}

// ISSUE: Inefficient DOM manipulation
function updateList(items) {
    const list = document.getElementById('itemList');
    
    // Inefficient: clearing and rebuilding entire list
    list.innerHTML = '';
    
    items.forEach(item => {
        // ISSUE: Creating elements in loop causes reflow
        const li = document.createElement('li');
        li.textContent = item.name;
        li.style.color = item.color; // Direct style manipulation
        list.appendChild(li); // Multiple DOM insertions
    });
}

// ISSUE: Synchronous heavy computation blocking UI
function processLargeDataset(data) {
    let processed = [];
    
    // Blocking operation - should use Web Workers or async processing
    for (let i = 0; i < data.length; i++) {
        for (let j = 0; j < 1000000; j++) {
            // Expensive computation
            processed.push(Math.sqrt(data[i] * j));
        }
    }
    
    return processed;
}

// ISSUE: Inefficient string concatenation
function buildLargeString(items) {
    let result = '';
    
    for (let i = 0; i < items.length; i++) {
        result += items[i] + '\n'; // Inefficient string concatenation
    }
    
    return result;
}

// ISSUE: Unnecessary re-renders and calculations
class IneffientComponent {
    constructor() {
        this.data = [];
        this.render();
    }
    
    addItem(item) {
        this.data.push(item);
        this.render(); // Re-renders entire component
    }
    
    render() {
        // Expensive calculation on every render
        const expensiveValue = this.data.reduce((acc, item) => {
            return acc + Math.pow(item.value, 3);
        }, 0);
        
        console.log('Rendering with value:', expensiveValue);
    }
}