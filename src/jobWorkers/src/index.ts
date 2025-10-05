import { ZBClient } from 'zeebe-node';
import { ProcessEntityValidator } from './processEntityValidator';

// Initialize Zeebe client
const zbc = new ZBClient();

// Initialize workers
const processEntityValidator = new ProcessEntityValidator(zbc);

// Start all workers
async function startWorkers() {
  try {
    console.log('🚀 Starting ProcessDSL Job Workers...');
    
    // Start process entity validator
    processEntityValidator.start();
    
    console.log('✅ All ProcessDSL Job Workers started successfully!');
    console.log('📋 Active workers:');
    console.log('   - process-entity-validator');
    console.log('\nPress Ctrl+C to stop the workers');
    
  } catch (error) {
    console.error('❌ Failed to start workers:', error);
    process.exit(1);
  }
}

// Graceful shutdown handling
async function shutdown() {
  console.log('\n🛑 Shutting down ProcessDSL Job Workers...');
  
  try {
    await processEntityValidator.stop();
    await zbc.close();
    
    console.log('✅ All workers stopped gracefully');
    process.exit(0);
  } catch (error) {
    console.error('❌ Error during shutdown:', error);
    process.exit(1);
  }
}

// Handle shutdown signals
process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);

// Start the workers
startWorkers().catch((error) => {
  console.error('❌ Failed to start ProcessDSL Job Workers:', error);
  process.exit(1);
});

// Export for programmatic use
export { ProcessEntityValidator };
