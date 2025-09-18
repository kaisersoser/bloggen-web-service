#!/usr/bin/env node
/**
 * Frontend EventSource Connection Test
 * 
 * Test if frontend can connect to SSE endpoint and receive notifications
 * using Node.js EventSource to simulate frontend behavior.
 */

const https = require('https');
const EventSource = require('eventsource');

// Configure to ignore SSL certificate issues for localhost
process.env["NODE_TLS_REJECT_UNAUTHORIZED"] = 0;

class FrontendSSEConnectionTester {
    constructor() {
        this.notifications = [];
        this.imageNotifications = [];
        this.eventSource = null;
    }
    
    async testFrontendSSEConnection() {
        console.log('🧪 FRONTEND SSE CONNECTION TEST');
        console.log('='.repeat(50));
        console.log('Testing EventSource connection from frontend perspective');
        console.log();
        
        try {
            // Step 1: Try to get a JWT token like frontend would
            console.log('🔑 Step 1: Getting JWT token...');
            const jwtToken = await this.getJWTToken();
            
            if (!jwtToken) {
                console.log('❌ Cannot proceed without JWT token');
                return;
            }
            
            // Step 2: Get an active task or use test task
            console.log('📋 Step 2: Getting active task...');
            const taskId = await this.getActiveTaskId();
            
            if (!taskId) {
                console.log('⚠️  No active task found, using test task ID');
                // Use a test task ID
                await this.connectToSSE('test-task-frontend-connection', jwtToken);
            } else {
                console.log(`✅ Found active task: ${taskId}`);
                await this.connectToSSE(taskId, jwtToken);
            }
            
        } catch (error) {
            console.log(`❌ Test failed: ${error.message}`);
        }
    }
    
    async getJWTToken() {
        // Read token from backend file since frontend endpoint isn't working
        try {
            const fs = require('fs');
            const path = require('path');
            const tokenPath = path.join(__dirname, '..', '..', 'valid_jwt_token.txt');
            const token = fs.readFileSync(tokenPath, 'utf8').trim();
            console.log(`✅ JWT token loaded from file: ${token.substring(0, 20)}...`);
            return token;
        } catch (error) {
            console.log(`❌ Error reading JWT token file: ${error.message}`);
            return null;
        }
    }
    
    async getActiveTaskId() {
        return new Promise((resolve, reject) => {
            const options = {
                hostname: 'localhost',
                port: 3001,
                path: '/api/tasks/active',
                method: 'GET',
                rejectUnauthorized: false
            };
            
            const req = https.request(options, (res) => {
                let data = '';
                res.on('data', (chunk) => data += chunk);
                res.on('end', () => {
                    try {
                        const response = JSON.parse(data);
                        if (response.tasks && response.tasks.length > 0) {
                            resolve(response.tasks[0].id);
                        } else {
                            resolve(null);
                        }
                    } catch (parseError) {
                        resolve(null);
                    }
                });
            });
            
            req.on('error', (error) => {
                resolve(null);
            });
            
            req.end();
        });
    }
    
    async connectToSSE(taskId, jwtToken) {
        return new Promise((resolve) => {
            console.log(`📡 Step 3: Connecting to SSE endpoint...`);
            
            const sseUrl = `https://localhost:5000/stream/${taskId}?token=${jwtToken}`;
            console.log(`🔗 SSE URL: ${sseUrl.substring(0, 80)}...`);
            
            this.eventSource = new EventSource(sseUrl);
            
            let notificationCount = 0;
            let imageCount = 0;
            const startTime = Date.now();
            
            this.eventSource.onopen = (event) => {
                console.log('✅ SSE connection opened successfully!');
                console.log('📡 Listening for notifications (30 second timeout)...');
                console.log();
            };
            
            this.eventSource.onmessage = (event) => {
                notificationCount++;
                const timestamp = new Date().toLocaleTimeString();
                
                try {
                    const data = JSON.parse(event.data);
                    const eventType = data.type || data.message_type || 'unknown';
                    
                    // Check for image notifications
                    const dataStr = JSON.stringify(data).toLowerCase();
                    const isImageEvent = eventType.toLowerCase().includes('image') || 
                                       dataStr.includes('image') ||
                                       dataStr.includes('unsplash') ||
                                       dataStr.includes('openai') ||
                                       dataStr.includes('dall');
                    
                    if (isImageEvent) {
                        imageCount++;
                        console.log(`[${timestamp}] 🖼️  IMAGE EVENT: ${eventType}`);
                        console.log(`    Data: ${JSON.stringify(data, null, 2).substring(0, 150)}...`);
                        this.imageNotifications.push({ timestamp, data });
                    } else {
                        console.log(`[${timestamp}] 📢 ${eventType}`);
                        if (data.message) {
                            console.log(`    Message: ${data.message.substring(0, 80)}...`);
                        }
                    }
                    
                    this.notifications.push({ timestamp, eventType, data });
                    
                } catch (parseError) {
                    console.log(`[${timestamp}] 📢 Raw: ${event.data.substring(0, 100)}...`);
                }
            };
            
            this.eventSource.onerror = (event) => {
                console.log('❌ SSE connection error');
                console.error('Error details:', event);
            };
            
            // Close connection after 30 seconds
            setTimeout(() => {
                this.eventSource.close();
                console.log();
                console.log('⏰ Test timeout after 30 seconds');
                this.analyzeResults(notificationCount, imageCount);
                resolve();
            }, 30000);
        });
    }
    
    analyzeResults(totalNotifications, imageNotifications) {
        console.log();
        console.log('🔍 FRONTEND SSE CONNECTION ANALYSIS');
        console.log('='.repeat(50));
        
        if (totalNotifications > 0) {
            console.log(`✅ Frontend CAN receive SSE notifications (${totalNotifications} total)`);
            
            if (imageNotifications > 0) {
                console.log(`✅ Image notifications ARE reaching frontend (${imageNotifications} image events)`);
                console.log('   → SSE delivery chain is working correctly!');
                console.log('   → Problem must be in frontend UI display or message handling');
            } else {
                console.log(`❌ Image notifications NOT reaching frontend`);
                console.log('   → Either no image events generated or filtering issue');
            }
            
            if (totalNotifications >= 10) {
                console.log(`✅ Good notification volume - SSE streaming active`);
            } else {
                console.log(`⚠️  Low notification volume - limited activity`);
            }
            
        } else {
            console.log(`❌ Frontend CANNOT receive SSE notifications`);
            console.log('   → SSE connection, authentication, or routing issue');
        }
        
        console.log();
        console.log('📋 NEXT DEBUGGING STEPS:');
        if (totalNotifications > 0) {
            if (imageNotifications > 0) {
                console.log('1. Check frontend UI components for notification display');
                console.log('2. Verify EventSource message handling in React components');
                console.log('3. Check console errors in browser developer tools');
            } else {
                console.log('1. Start a blog generation to trigger image notifications');
                console.log('2. Check if image events are being generated');
            }
        } else {
            console.log('1. Check SSE endpoint authentication');
            console.log('2. Verify CORS settings for cross-origin SSE');
            console.log('3. Check network connectivity between frontend and backend');
        }
        
        console.log();
        console.log('Frontend SSE connection test completed!');
    }
}

// Run the test
const tester = new FrontendSSEConnectionTester();
tester.testFrontendSSEConnection().catch(console.error);