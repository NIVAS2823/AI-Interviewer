import { healthAPI } from './lib/api';

async function testConnection() {
  try {
    console.log('Testing backend connection...');
    const response = await healthAPI.check();
    console.log('✅ Backend connected:', response.data);
    return true;
  } catch (error) {
    console.error('❌ Backend connection failed:', error.message);
    return false;
  }
}

testConnection();